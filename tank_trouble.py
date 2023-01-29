"""
作者：讨啄的白菜
日期：2022年08月13日
"""
import random
# import cv2
import pygame
import pymunk
import pymunk.pygame_util
import math
from pymunk.vec2d import Vec2d
import numpy as np
from pymunk.autogeometry import march_soft

# help(pymunk.body)
pygame.init()

WIDTH, HEIGHT = 1536, 800
window = pygame.display.set_mode((WIDTH, HEIGHT))
space = pymunk.Space()
pygame.display.set_caption('坦克动荡')

mouse_joint = None
mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

collision_types = {
    "wall": 0,
    "tank": 1,
    "bullet": 2,
    "prop": 3,
    "laserBullet": 4,
    "missile": 5,
    "brokenBullet": 6,
    "stickBullet": 7,
}

prop_types = {
    "gatling": 1,
    "frag": 2,
    "scatter": 3,
    "laser": 4,
    "death": 5,
    "rc": 6,
    "speed": 7,
    "teleport": 8,
    "broken": 9,
}

# tank1_img = pygame.image.load("tankRed.png")
font = pygame.font.SysFont("Arial", 30)
mouse_visible = True

bullets = []
props = []
remove_obj = set([])

red_win = 0
green_win = 0
props_num = 5
game_time = 0

class Prop:
    def __init__(self, prop_type, position):
        self.prop_type = prop_types[prop_type]
        self.image_file = 'image/' + prop_type + '.png'
        self.image = pygame.image.load(self.image_file)
        self.rect = self.image.get_rect()
        self.position = position
        self.rect.center = self.position

        self.prop_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.prop_body.prop_type = self.prop_type  # 道具编号
        self.prop_body.position = self.position
        self.prop_shape = pymunk.Circle(self.prop_body, 15)
        self.prop_shape.density = 0.1
        self.prop_shape.elasticity = 1
        self.prop_shape.friction = 0
        self.prop_shape.color = pygame.Color("black")
        self.prop_shape.collision_type = collision_types["prop"]
        space.add(self.prop_body, self.prop_shape)

    def draw(self):
        window.blit(self.image, self.rect)

    def update(self):
        global props_num
        if self.prop_shape in remove_obj:
            props.remove(self)
            props_num += 1

class Bullet:
    def __init__(self, tank):
        self.speed = 170
        self.bullet_body = pymunk.Body()
        self.bullet_body.position = tank.tank_body.position + tank.tank_body.rotation_vector * 24

        self.bullet_shape = pymunk.Circle(self.bullet_body, 3)
        self.bullet_shape.density = 0.1
        self.bullet_shape.elasticity = 1
        self.bullet_shape.friction = 0
        self.bullet_shape.color = pygame.Color("black")
        self.bullet_shape.collision_type = collision_types["bullet"]
        self.bullet_shape.father = self


        self.bullet_body.velocity = (tank.tank_body.rotation_vector) * self.speed
        self.max_time = 500
        self.time = self.max_time

    def update(self, space):
        self.time -= 1
        if self.time <= 0 and self.bullet_shape in space.shapes:
            space.remove(self.bullet_shape.body, self.bullet_shape)
            bullets.remove(self)

class FragBullet():
    def __init__(self, tank):
        self.bullet_body = pymunk.Body()
        self.bullet_body.explode = self.explode
        self.tank_body = self.bullet_body
        self.bullet_body.position = tank.tank_body.position + tank.tank_body.rotation_vector * 30

        self.bullet_shape = pymunk.Circle(self.bullet_body, 6)
        self.bullet_shape.density = 0.1
        self.bullet_shape.elasticity = 1
        self.bullet_shape.friction = 0
        self.bullet_shape.color = pygame.Color("black")
        self.bullet_shape.collision_type = collision_types["bullet"]

        self.speed = 120
        self.bullet_body.velocity = (tank.tank_body.rotation_vector) * self.speed
        self.bullet_shape.father = self
        self.max_time = 500
        self.time = self.max_time
    def update(self, space):
        self.time -= 1
        if self.time <= 0 and self.bullet_shape in space.shapes:
            self.explode()
            space.remove(self.bullet_shape.body, self.bullet_shape)
            bullets.remove(self)

    def explode(self):
        for i in range(20):
            bullet = Bullet(self)
            bullet.bullet_body.position = self.bullet_body.position
            angle = random.uniform(0, 2*math.pi)
            bullet.bullet_body.velocity = Vec2d(math.cos(angle), math.sin(angle)) * 170
            space.add(bullet.bullet_body, bullet.bullet_shape)
            bullets.append(bullet)

class LaserBullet():
    def __init__(self, tank):
        self.bullet_body = pymunk.Body()
        self.tank_body = self.bullet_body
        self.bullet_body.position = tank.tank_body.position + tank.tank_body.rotation_vector * 30

        self.bullet_shape = pymunk.Circle(self.bullet_body, 6)
        self.bullet_shape.density = 0.1
        self.bullet_shape.elasticity = 1
        self.bullet_shape.friction = 0
        self.bullet_shape.color = pygame.Color("white")
        self.bullet_shape.tank_color = tank.tank_shape.color
        self.bullet_shape.collision_type = collision_types["laserBullet"]

        self.speed = 700
        self.bullet_body.velocity = (tank.tank_body.rotation_vector) * self.speed
        self.bullet_shape.father = self
        self.max_time = 500
        self.time = self.max_time
        self.laserList = [self.bullet_body.position]
        self.bullet_shape.laserList = self.laserList
    def update(self, space):
        self.time -= 1
        if self.time <= 0 and self.bullet_shape in space.shapes:
            space.remove(self.bullet_shape.body, self.bullet_shape)
            bullets.remove(self)

class Laser():
    def __init__(self, p1, p2, color, rad=2):
        self.laser_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.laser_body.position = p1  # (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2

        self.laser_shape = pymunk.Segment(self.laser_body, (0, 0), (p2[0] - p1[0], p2[1] - p1[1]), rad)
        self.laser_shape.density = 0.1
        self.laser_shape.elasticity = 1
        self.laser_shape.friction = 0
        self.laser_shape.color = pygame.Color(color)
        self.laser_shape.collision_type = collision_types["bullet"]
        self.bullet_shape = self.laser_shape
        self.bullet_shape.father = self
        self.broke_available = True
        self.max_time = 100
        self.time = self.max_time
    def update(self, space):
        self.time -= 1
        if self.time <= 0 and self.laser_shape in space.shapes:
            space.remove(self.laser_shape.body, self.laser_shape)
            bullets.remove(self)

class RC():
    def __init__(self, tank):
        self.speed = 120
        self.bullet_body = pymunk.Body()
        self.bullet_body.position = tank.tank_body.position + tank.tank_body.rotation_vector * 35
        self.tank = tank
        self.bullet_body.tank = tank
        self.bullet_body.father = self
        self.bullet_shape = pymunk.Circle(self.bullet_body, 10)
        self.bullet_shape.father = self
        self.bullet_shape.density = 0.1
        self.bullet_shape.elasticity = 0.1
        self.bullet_shape.friction = 0
        self.bullet_shape.color = pygame.Color("white")
        self.bullet_shape.collision_type = collision_types["missile"]

        if self.tank.tank_shape.color == (255, 0, 0, 100):
            self.ori_image = pygame.image.load("image/red_missile.png")
        else:
            self.ori_image = pygame.image.load("image/green_missile.png")
        self.rect = self.ori_image.get_rect()
        self.rect.center = self.bullet_body.position

        self.angle = calculate_angle((0, 0), self.tank.tank_body.rotation_vector)
        self.angle = 360 - math.degrees(self.angle)
        self.image = pygame.transform.rotate(self.ori_image, self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = self.bullet_body.position

        self.bullet_body.velocity = (tank.tank_body.rotation_vector) * self.speed
        self.angular_velocity = 3
        self.time = 1000
        self.col_time = self.time
    def update(self, space):
        self.time -= 1
        # self.bullet_body.velocity = 0, 0
        self.bullet_body.angular_velocity = 0
        if self.time <= self.col_time - 10:
            self.bullet_body.velocity = self.tank.tank_body.rotation_vector * self.speed
            # self.bullet_body.apply_force_at_world_point(unitization(*self.bullet_body.velocity) * -1000, (0, 0))
            # if math.hypot(*self.bullet_body.velocity) <= 170:
            #     self.bullet_body.apply_force_at_world_point(self.tank.tank_body.rotation_vector * 3000, (0, 0))
            # if math.hypot(*self.bullet_body.velocity) <= 100:
            #     self.bullet_body.apply_impulse_at_world_point(self.tank.tank_body.rotation_vector * 300, (0, 0))


        self.angle = calculate_angle((0, 0), self.tank.tank_body.rotation_vector)
        self.angle = 360 - math.degrees(self.angle)
        self.image = pygame.transform.rotate(self.ori_image, self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = self.bullet_body.position

        # self.bullet_body.velocity = self.bullet_body.rotation_vector[1] * self.speed, self.bullet_body.rotation_vector[0] * -self.speed
        if self.time <= 0 and self.bullet_shape in space.shapes:
            space.remove(self.bullet_shape.body, self.bullet_shape)
            bullets.remove(self)
    def draw_image(self):
        if self.bullet_shape in space.shapes:
            window.blit(self.image, self.rect)

class BrokenBullet():
    def __init__(self, tank):
        self.bullet_body = pymunk.Body()
        self.bullet_body.position = tank.tank_body.position + tank.tank_body.rotation_vector * 24

        self.bullet_shape = pymunk.Circle(self.bullet_body, 3)
        self.bullet_shape.density = 0.1
        self.bullet_shape.elasticity = 1
        self.bullet_shape.friction = 0
        self.bullet_shape.color = pygame.Color("black")
        self.bullet_shape.collision_type = collision_types["brokenBullet"]
        self.bullet_shape.father = self

        self.speed = 170
        self.bullet_body.velocity = (tank.tank_body.rotation_vector) * self.speed
        self.broke_available = True
        self.time = 500

    def update(self, space):
        self.time -= 1
        if self.time <= 0 and self.bullet_shape in space.shapes:
            space.remove(self.bullet_shape.body, self.bullet_shape)
            bullets.remove(self)

class Tank:
    def __init__(self, color):
        self.speed = 100
        self.angular_velocity = 3

        self.death_lasers = []

        self.fire_available = False
        self.move_available = False
        self.rotate_available = False
        self.is_fire_death_laser = False
        self.is_fire_rc = False
        self.is_gatling = False
        self.is_scatter = False

        self.tank_body = pymunk.Body(body_type=pymunk.Body.DYNAMIC)
        self.tank_body.prop_type = 0
        self.tank_body.position = (random.randint(100, 1400), random.randint(100, 800))
        self.tank_body.velocity = 0, 0
        self.tank_body.angular_velocity = 0
        self.tank_body.father = self
        self.elasticity = 0.2

        # tank_shape = pymunk.Poly.create_box(tank_body, (20, 15))
        self.tank_shape = pymunk.Poly.create_box(self.tank_body, (28, 21))
        self.tank_shape.density = 0.1
        self.tank_shape.elasticity = self.elasticity
        self.tank_shape.color = color
        self.tank_shape.collision_type = collision_types["tank"]

        self.tank_shape_2 = pymunk.Circle(self.tank_body, 7)
        self.tank_shape_2.density = 0.1
        self.tank_shape_2.elasticity = self.elasticity
        self.tank_shape_2.collision_type = collision_types["tank"]
        self.tank_shape_2.color = (int(color[0] * 200 / 255), int(color[1] * 200 / 255), int(color[2] * 200 / 255), color[3])

        self.tank_shape_3 = pymunk.Segment(self.tank_body, (-5, 0), (20, 0), 2)
        self.tank_shape_3.density = 0.1
        self.tank_shape_3.elasticity = self.elasticity
        self.tank_shape_3.collision_type = collision_types["tank"]
        self.tank_shape_3.color = (int(color[0] * 123 / 255), int(color[1] * 123 / 255), int(color[2] * 123 / 255), color[3])

        self.col_time = 0

    def fire(self):
        if self.tank_body.prop_type in (0, 1, 7, 8):
            if self.is_scatter:
                self.fire_scatter(Bullet)
            else:
                bullet = Bullet(self)
                space.add(bullet.bullet_body, bullet.bullet_shape)
                bullets.append(bullet)
        elif self.tank_body.prop_type == 2:
            self.fire_frag()
        elif self.tank_body.prop_type == 4:
            self.fire_laser()
        elif self.tank_body.prop_type == 5:
            self.fire_death()
        elif self.tank_body.prop_type == 6:
            self.fire_rc()
        elif self.tank_body.prop_type == 9:
            self.fire_broken()

    def fire_frag(self):
        if self.is_scatter:
            self.fire_scatter(FragBullet)
        else:
            bullet = FragBullet(self)
            space.add(bullet.bullet_body, bullet.bullet_shape)
            bullets.append(bullet)

    def fire_scatter(self, Type):
        vec = self.tank_body.rotation_vector
        angle = math.atan2(*vec[::-1])
        angle = math.degrees(angle)
        for _ in range(5):
            bullet = Type(self)
            ang = angle + random.uniform(-15, 15)
            ang = math.radians(ang)
            bullet.bullet_body.velocity = Vec2d(math.cos(ang), math.sin(ang)) * bullet.speed
            space.add(bullet.bullet_body, bullet.bullet_shape)
            bullets.append(bullet)

    def fire_laser(self):
        if self.is_scatter:
            self.fire_scatter(LaserBullet)
        else:
            bullet = LaserBullet(self)
            space.add(bullet.bullet_body, bullet.bullet_shape)
            bullets.append(bullet)

    def fire_death(self):
        self.death_lasers.clear()
        if self.is_scatter:
            vec = self.tank_body.rotation_vector
            angle = math.atan2(*vec[::-1])
            angle = math.degrees(angle)
            for _ in range(5):
                ang = angle -14 + _ * 7
                ang = math.radians(ang)
                p1 = self.tank_body.position + Vec2d(math.cos(ang), math.sin(ang)) * 30
                length = Vec2d(math.cos(ang), math.sin(ang)) * 2000
                p2 = p1[0] + length[0], p1[1] + length[1]
                laser = Laser(p1, p2, self.tank_shape.color, 4)
                space.add(laser.laser_body, laser.laser_shape)
                bullets.append(laser)
                self.death_laser = laser
                self.death_lasers.append(laser)
        else:
            p1 = self.tank_body.position + self.tank_body.rotation_vector * 30
            length = self.tank_body.rotation_vector * 2000
            p2 = p1[0] + length[0], p1[1] + length[1]
            laser = Laser(p1, p2, self.tank_shape.color, 4)
            space.add(laser.laser_body, laser.laser_shape)
            bullets.append(laser)
            self.death_laser = laser
            self.death_lasers.append(laser)
        self.is_fire_death_laser = True

    def fire_rc(self):
        rc = RC(self)
        space.add(rc.bullet_body, rc.bullet_shape)
        bullets.append(rc)
        self.rc = rc
        self.is_fire_rc = True

    def fire_broken(self):
        if self.is_scatter:
            self.fire_scatter(BrokenBullet)
        else:
            bullet = BrokenBullet(self)
            space.add(bullet.bullet_body, bullet.bullet_shape)
            bullets.append(bullet)

    def teleport(self):
        self.tank_body.position = self.tank_body.position + self.tank_body.rotation_vector * 50

    def update(self):
        if self.is_fire_death_laser:
            if self.death_laser.time <= 0:
                self.is_fire_death_laser = False
            self.move_available = False
            self.fire_available = False
            self.angular_velocity = 0.1
            if self.is_scatter:
                vec = self.tank_body.rotation_vector
                angle = math.atan2(*vec[::-1])
                angle = math.degrees(angle)
                for _ in range(5):
                    ang = angle - 14 + _ * 7
                    ang = math.radians(ang)
                    p1 = self.tank_body.position + Vec2d(math.cos(ang), math.sin(ang)) * 30
                    length = Vec2d(math.cos(ang), math.sin(ang)) * 2000
                    p2 = p1[0] + length[0], p1[1] + length[1]
                    self.death_lasers[_].laser_body.position = p1
                    self.death_lasers[_].laser_shape.unsafe_set_endpoints((0, 0), p2 - p1)
                    if self.death_lasers[_].laser_shape in space.shapes:
                        space.remove(self.death_lasers[_].laser_body, self.death_lasers[_].laser_shape)
                        space.add(self.death_lasers[_].laser_shape, self.death_lasers[_].laser_body)
            else:
                p1 = self.tank_body.position + self.tank_body.rotation_vector * 30
                length = self.tank_body.rotation_vector * 2000
                p2 = p1[0] + length[0], p1[1] + length[1]
                self.death_laser.laser_body.position = p1
                self.death_laser.laser_shape.unsafe_set_endpoints((0, 0), p2 - p1)
                if self.death_laser.laser_shape in space.shapes:
                    space.remove(self.death_laser.laser_body, self.death_laser.laser_shape)
                    space.add(self.death_laser.laser_shape, self.death_laser.laser_body)
            # print(self.death_laser.laser_shape.a, self.death_laser.laser_shape.b)
        elif self.is_fire_rc:
            if self.rc.bullet_shape not in space.shapes:
                self.is_fire_rc = False
            self.move_available = False
            self.fire_available = False
            # self.rotate_available = False
        else:
            self.angular_velocity = 3

def sub_tuple(p1, p2):
    return p1[0] - p2[0], p1[1] - p2[1]

def time_stop():
    for b in bullets:
        b.bullet_body.velocity = (0, 0)

def unitization(x, y):
    # mo = math.sqrt(x ** 2 + y ** 2)
    # return Vec2d(x / mo, y / mo)
    return p2vec((0, 0), (x, y))

def p2vec(p1, p2):
    angle = calculate_angle(p1, p2)
    vec = (math.cos(angle), math.sin(angle))
    return Vec2d(*vec)

def calculate_distance(p1, p2):
    return math.sqrt((p2[1] - p1[1])**2 + (p2[0] - p1[0])**2)

def calculate_angle(p1, p2):
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

def draw(space, window, draw_options, line):
    if line:
        pygame.draw.line(window, "black", line[0], line[1], 3)
    space.debug_draw(draw_options)
    # 绘制道具
    for p in props:
        p.draw()
    for b in bullets:
        if hasattr(b, "draw_image"):
            b.draw_image()
    window.blit(
        font.render("red    : %d" % red_win, True, pygame.Color("red")),
        (1400, 10)
    )
    window.blit(
        font.render("green: %d" % green_win, True, pygame.Color("green")),
        (1400, 50)
    )
    # window.blit(pygame.transform.rotate(tank1_img, 90 - np.angle(tank1.rotation_vector[0] + 1j*tank1.rotation_vector[1], deg=True)), tank1.position - (12, 7))
    pygame.display.update()

def create_boundaries(space, width, height):
    rects = [
        [(width/2, height - 10), (width, 20)],
        [(width/2, 10), (width, 20)],
        [(10, height/2), (20, height)],
        [(width - 10, height/2), (20, height)],
    ]

    for pos, size in rects:
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = pos
        shape = pymunk.Poly.create_box(body, size)
        shape.elasticity = 0.4
        shape.friction = 1
        space.add(body, shape)

def create_structure(space, width, height):
    BROWN = (139, 69, 19, 100)
    rects = [
        [(600, height - 120), (40, 200), BROWN, 100],
        [(900, height - 120), (40, 200), BROWN, 100],
        [(750, height - 240), (340, 40), BROWN, 150],
    ]

    for pos, size, color, mass in rects:
        body = pymunk.Body()
        body.position = pos
        shape = pymunk.Poly.create_box(body, size, radius=2)
        shape.color = color
        shape.mass = mass
        shape.elasticity = 0.4
        space.add(body, shape)

def create_ball(space, radius, pos):
    body = pymunk.Body()
    body.position = pos
    shape = pymunk.Circle(body, radius)
    shape.density = 0.1
    shape.elasticity = 1
    shape.friction = 0
    shape.color = (255, 0, 0, 100)
    space.add(body, shape)
    return shape

def create_ret(space, pos, size, flag):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = pos
    if flag == 0:
        # body.position = pos + (4//2, size//2)
        shape = pymunk.Poly.create_box(body, (4, size), radius=1)  # 竖
    else:
        # body.position = pos + (size // 2, 4 // 2)
        shape = pymunk.Poly.create_box(body, (size, 4), radius=1)

    shape.elasticity = 1
    shape.density = 0.1
    shape.color = (77, 77, 77, 100)
    space.add(body, shape)
    return shape

def create_seg(space, pos, size, flag):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = pos
    rad = 4
    if flag == 0:
        shape = pymunk.Segment(body, (0, 0), (0, size), radius=rad)
    else:
        shape = pymunk.Segment(body, (0, 0), (size, 0), radius=rad)
    shape.collision_type = collision_types["wall"]
    shape.elasticity = 1
    shape.density = 0.1
    shape.color = (77, 77, 77, 100)
    space.add(body, shape)
    return shape

# def create_map(space):
#     image = cv2.imread("image/10x10.png", cv2.IMREAD_GRAYSCALE)
#     image = cv2.resize(image, (image.shape[0]*2, image.shape[1]*2))
#     map = image < 127
#     # map_body = pymunk.Body()
#     # space.add(map_body)
#     def sample_func(point):
#         x = int(point[0])
#         y = int(point[1])
#         return 1 if map[y][x] else 0
#
#     pl_set = march_soft(pymunk.BB(0, 0, map.shape[0], map.shape[1]), map.shape[0], map.shape[1], .5, sample_func)
#     for poly_line in pl_set:
#         for i in range(len(poly_line) - 1):
#             a = poly_line[i]
#             b = poly_line[i + 1]
#             segment = pymunk.Segment(space.static_body, a, b, 1)
#             segment.density = 0.1
#             space.add(segment)
#     # for i in range(map.shape[0]):
#     #     for j in range(map.shape[1]):
#     #         if map[i][j]:
#     #             create_ret(space, (j, i), (1, 1))
def create_map2(space):
    create_ret(space, (0,0), 164, 0)
    for _ in range(500):
        pos = (random.randint(0, 30) * 50, random.randint(0, 20) * 50)
        size = random.randint(1, 1) * 50
        flag = random.choice((0, 1))
        create_seg(space, pos, size, flag)
    pass


def create_tank(color):
    tank = Tank(color)
    space.add(tank.tank_shape, tank.tank_shape_2, tank.tank_shape_3, tank.tank_body)
    return tank

def create_prop():
    global props_num
    prop = Prop(random.choice(list(prop_types)), (random.randint(0, 1536), random.randint(0, 800)))
    props_num -= 1
    props.append(prop)

def create_prop_by_mouse(prop_type):
    global props_num
    prop = Prop(prop_type, pygame.mouse.get_pos())
    props.append(prop)

def create_stick_figure(space):
    shapes = []
    bodies = []
    joints = []

    # head = pymunk.Body()
    # bodies.append(head)
    # head.position = (300, 500)
    # head_shape = pymunk.Circle(head, 20)
    # shapes.append(head_shape)

    torso = pymunk.Body()
    bodies.append(torso)
    torso.position = (300, 520)
    torso_shape = pymunk.Segment(torso, (0, 0), (0, 70), 5)
    torso_shape.color = (0, 0, 200, 100)
    tou_shape = pymunk.Circle(torso, 20, (0, -20))
    tou_shape.color = (200, 0, 0, 100)
    shapes.append(torso_shape)
    shapes.append(tou_shape)

    left_arm = pymunk.Body()
    bodies.append(left_arm)
    left_arm.position = (300, 520)
    left_arm_shape = pymunk.Segment(left_arm, (0, 0), (-25, 30), 5)
    left_arm_shape.color = (0, 0, 200, 100)
    shapes.append(left_arm_shape)

    left_arm_2 = pymunk.Body()  # 左下臂
    bodies.append(left_arm_2)
    left_arm_2.position = (275, 550)
    left_arm_2_shape = pymunk.Segment(left_arm_2, (0, 0), (-25, 30), 5)
    left_arm_2_shape.collision_type = collision_types["stickBullet"]
    left_arm_2_shape.color = (200, 0, 0, 100)
    shapes.append(left_arm_2_shape)

    right_arm = pymunk.Body()
    bodies.append(right_arm)
    right_arm.position = (300, 520)
    right_arm_shape = pymunk.Segment(right_arm, (0, 0), (25, 30), 5)
    right_arm_shape.color = (0, 0, 200, 100)
    shapes.append(right_arm_shape)

    right_arm_2 = pymunk.Body()  # 右下臂
    bodies.append(right_arm_2)
    right_arm_2.position = (325, 550)
    right_arm_2_shape = pymunk.Segment(right_arm_2, (0, 0), (25, 30), 5)
    right_arm_2_shape.collision_type = collision_types["stickBullet"]
    right_arm_2_shape.color = (200, 0, 0, 100)
    shapes.append(right_arm_2_shape)

    left_leg = pymunk.Body()
    bodies.append(left_leg)
    left_leg.position = (300, 590)
    left_leg_shape = pymunk.Segment(left_leg, (0, 0), (-25, 30), 6)
    left_leg_shape.color = (0, 0, 200, 100)
    shapes.append(left_leg_shape)

    left_leg_2 = pymunk.Body()
    bodies.append(left_leg_2)
    left_leg_2.position = (275, 620)
    left_leg_2_shape = pymunk.Segment(left_leg_2, (0, 0), (-25, 30), 6)
    left_leg_2_shape.collision_type = collision_types["stickBullet"]
    left_leg_2_shape.color = (200, 0, 0, 100)
    shapes.append(left_leg_2_shape)

    right_leg = pymunk.Body()
    bodies.append(right_leg)
    right_leg.position = (300, 590)
    right_leg_shape = pymunk.Segment(right_leg, (0, 0), (25, 30), 6)
    right_leg_shape.color = (0, 0, 200, 100)
    shapes.append(right_leg_shape)

    right_leg_2 = pymunk.Body()
    bodies.append(right_leg_2)
    right_leg_2.position = (325, 620)
    right_leg_2_shape = pymunk.Segment(right_leg_2, (0, 0), (25, 30), 6)
    right_leg_2_shape.collision_type = collision_types["stickBullet"]
    right_leg_2_shape.color = (200, 0, 0, 100)
    shapes.append(right_leg_2_shape)

    for shape in shapes:
        shape.friction = 1
        shape.mass = 3
        shape.elasticity = 1
        shape.filter = pymunk.ShapeFilter(group=1)

    # head_torso_joint = pymunk.PivotJoint(head, torso, (300, 500))
    # joints.append(head_torso_joint)

    torso_left_arm_joint = pymunk.PivotJoint(torso, left_arm, (300, 520))
    joints.append(torso_left_arm_joint)

    torso_right_arm_joint = pymunk.PivotJoint(torso, right_arm, (300, 520))
    joints.append(torso_right_arm_joint)

    left_arm_12_joint = pymunk.PivotJoint(left_arm, left_arm_2, (275, 550))
    joints.append(left_arm_12_joint)

    right_arm_12_joint = pymunk.PivotJoint(right_arm, right_arm_2, (325, 550))
    joints.append(right_arm_12_joint)

    torso_left_leg_joint = pymunk.PivotJoint(torso, left_leg, (300, 590))
    # torso_left_leg_RatchetJoint =  pymunk.RatchetJoint(left_leg, torso, 0, math.pi / 3)
    joints.append(torso_left_leg_joint)
    # joints.append(torso_left_leg_RatchetJoint)

    torso_right_leg_joint = pymunk.PivotJoint(torso, right_leg, (300, 590))
    # torso_right_leg_RatchetJoint = pymunk.RatchetJoint(right_leg, torso, 0, math.pi / 3)
    joints.append(torso_right_leg_joint)
    # joints.append(torso_right_leg_RatchetJoint)

    left_leg_12_joint = pymunk.PivotJoint(left_leg, left_leg_2, (275, 620))
    left_leg_12_joint_2 = pymunk.RatchetJoint(left_leg_2, left_leg, 0, -math.pi)
    joints.append(left_leg_12_joint)
    joints.append(left_leg_12_joint_2)
    left_leg_12_joint_3 = pymunk.DampedRotarySpring(left_leg, left_leg_2, -math.pi, 3000, 60)
    joints.append(left_leg_12_joint_3)


    right_leg_12_joint = pymunk.PivotJoint(right_leg, right_leg_2, (325, 620))
    right_leg_12_joint_2 = pymunk.RatchetJoint(right_leg_2, right_leg, 0, -math.pi)
    joints.append(right_leg_12_joint)
    joints.append(right_leg_12_joint_2)
    right_leg_12_joint_3 = pymunk.DampedRotarySpring(right_leg, right_leg_2, -math.pi, 3000, 60)
    joints.append(right_leg_12_joint_3)

    space.add(*bodies, *shapes, *joints)

    return torso

def create_swing_ball(space):
    rotation_center_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    rotation_center_body.position = (300, 300)

    body = pymunk.Body()
    body.position = (300, 300)
    line = pymunk.Segment(body, (0, 0), (255, 0), 5)
    circle = pymunk.Circle(body, 40, (255, 0))
    line.friction = 1
    circle.friction = 1
    line.mass = 8
    circle.mass = 30
    circle.elasticity = 0.95
    rotation_center_joint = pymunk.PinJoint(body, rotation_center_body, (0, 0), (0, 0))
    space.add(circle, line, body, rotation_center_joint)

def restart(space, tank1, tank2):
    global props_num
    global game_time
    is_end = 0
    game_time = 0
    try:
        props.clear()
        bullets.clear()
        props_num = 5
        for item in space.shapes:
            space.remove(item)
        # space.remove(*tank1.tank_body.shapes, *tank2.tank_body.shapes, tank1.tank_body, tank2.tank_body)
        space.shapes.clear()
    except:
        pass
    for s in space.shapes[:]:
        try:
            space.remove(s.body, s)
        except:
            continue
    t1 = create_tank((255, 0, 0, 100))
    t2 = create_tank((0, 255, 0, 100))
    create_map2(space)

    return t1, t2, is_end

def restart_train(space, tank1, tank2):
    global props_num
    global game_time
    is_end = 0
    game_time = 0
    try:
        props.clear()
        bullets.clear()
        props_num = 5
        for item in space.shapes:
            space.remove(item)
        # space.remove(*tank1.tank_body.shapes, *tank2.tank_body.shapes, tank1.tank_body, tank2.tank_body)
        space.shapes.clear()
    except:
        pass
    for s in space.shapes[:]:
        try:
            space.remove(s.body, s)
        except:
            continue
    t1 = create_tank((255, 0, 0, 100))
    t2 = create_tank((0, 255, 0, 100))

    return t1, t2, is_end

def run():
    run = True
    clock = pygame.time.Clock()
    fps = 60
    dt = 1 / fps

    # space.gravity = (0, 0)

    # create_boundaries(space, width, height)
    # create_structure(space, width, height)
    # stick_figure = create_stick_figure(space)
    tank1 = create_tank((255, 0, 0, 100))
    tank2 = create_tank((0, 255, 0, 100))
    # create_ball(space, 10, (50, 50))

    draw_options = pymunk.pygame_util.DrawOptions(window)

    translation = pymunk.Transform()
    scaling = 1

    pressed_pos = None
    ball = None

    cnt = 1

    def remove_tank(arbiter, space, data):
        tank_shape = arbiter.shapes[0]
        space.remove(tank_shape)

    def remove_bullet(arbiter, space, data):
        bullet_shape = arbiter.shapes[1]
        tank_shape = arbiter.shapes[0]
        if hasattr(bullet_shape.body, 'explode'):
            bullet_shape.body.explode()
        # space.remove(bullet_shape, bullet_shape.body)
        remove_obj.add(bullet_shape)
        if bullet_shape in bullets:
            bullets.remove(bullet_shape)
        remove_obj.add(tank_shape)

    def remove_prop(arbiter, space, data):
        tank_shape = arbiter.shapes[0]
        prop_shape = arbiter.shapes[1]
        type = prop_shape.body.prop_type
        if type == prop_types["gatling"]:
            tank_shape.body.father.is_gatling = True
        elif type == prop_types["scatter"]:
            tank_shape.body.father.is_scatter = True
        else:
            tank_shape.body.prop_type = prop_shape.body.prop_type
        remove_obj.add(prop_shape)

    def reflect(arbiter, space, data):
        wall_shape = arbiter.shapes[1]
        laserBulletShape = arbiter.shapes[0]
        laserList = laserBulletShape.laserList
        if not laserBulletShape.body.position in laserList:
            laserList.append(laserBulletShape.body.position)
            laser = Laser(tuple(laserList[-1]), tuple(laserList[-2]), laserBulletShape.tank_color)
            space.add(laser.laser_body, laser.laser_shape)
            bullets.append(laser)

    def no_coll(arbiter, space, data):
        return False

    def set_velocity_zero(arbiter, space, data):  # 阻止物体穿墙
        bullet_shape = arbiter.shapes[0]
        bullet_shape.father.col_time = bullet_shape.father.time

    def broke_wall(arbiter, space, data):
        bullet_shape = arbiter.shapes[0]
        wall_shape = arbiter.shapes[1]
        if bullet_shape.father.broke_available:
            # bullet_shape.father.broke_available = False
            remove_obj.add(wall_shape)

    def anti_col(arbiter, space, data):
        tank_shape = arbiter.shapes[0]
        if isinstance(tank_shape, pymunk.Segment):
            tank_shape.body.father.col_time = game_time

    def solve_bullet_through_wall(arbiter, space, data):
        bullet_shape = arbiter.shapes[0]
        if bullet_shape.father.max_time - bullet_shape.father.time <= 1:
            remove_obj.add(bullet_shape)

    def col_stick_tank(arbiter, space, data):
        bullet_shape = arbiter.shapes[1]
        tank_shape = arbiter.shapes[0]
        if bullet_shape in bullets:
            bullets.remove(bullet_shape)
        remove_obj.add(tank_shape)

    h1 = space.add_collision_handler(collision_types["tank"], collision_types["bullet"])
    h2 = space.add_collision_handler(collision_types["tank"], collision_types["prop"])
    h3 = space.add_collision_handler(collision_types["laserBullet"], collision_types["wall"])
    h4 = space.add_collision_handler(collision_types["laserBullet"], collision_types["bullet"])
    h5 = space.add_collision_handler(collision_types["laserBullet"], collision_types["tank"])
    h6 = space.add_collision_handler(collision_types["laserBullet"], collision_types["prop"])
    h7 = space.add_collision_handler(collision_types["bullet"], collision_types["prop"])
    h8 = space.add_collision_handler(collision_types["laserBullet"], collision_types["laserBullet"])
    h9 = space.add_collision_handler(collision_types["missile"], collision_types["wall"])
    h10 = space.add_collision_handler(collision_types["missile"], collision_types["prop"])
    h11 = space.add_collision_handler(collision_types["missile"], collision_types["tank"])
    h12 = space.add_collision_handler(collision_types["brokenBullet"], collision_types["wall"])
    h14 = space.add_collision_handler(collision_types["brokenBullet"], collision_types["tank"])
    h15 = space.add_collision_handler(collision_types["brokenBullet"], collision_types["prop"])
    h16 = space.add_collision_handler(collision_types["tank"], collision_types["wall"])
    h17 = space.add_collision_handler(collision_types["bullet"], collision_types["wall"])
    h18 = space.add_collision_handler(collision_types["tank"], collision_types["stickBullet"])

    h1.post_solve = h11.post_solve = h14.post_solve = remove_bullet
    h2.post_solve = remove_prop
    h3.post_solve = reflect
    h4.begin = h5.begin = h6.begin = h7.begin = h8.begin = h10.begin = h15.begin = no_coll
    h9.post_solve = set_velocity_zero
    h12.post_solve = broke_wall
    h16.post_solve = anti_col
    h17.post_solve = solve_bullet_through_wall
    h18.post_solve = col_stick_tank

    create_map2(space)
    # restart_train(space, tank1, tank2)
    is_end = 0

    while run:
        global game_time
        global mouse_visible
        game_time += 1
        window.fill("white")
        line = None
        if cnt == 1:
            mouse_joint = None
            mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            cnt = 0
        if ball and pressed_pos:
            line = [pygame.mouse.get_pos(), pressed_pos]

        # stick_figure.apply_force_at_world_point((0, -27000), stick_figure.position + (0, -100))

        key = pygame.key.get_pressed()

        if tank1.tank_body.prop_type != 7:
            tank1.tank_body.velocity = 0, 0
        tank1.tank_body.angular_velocity = 0
        tank1.fire_available = False
        tank1.move_available = False
        tank1.rotate_available = False
        if tank2.tank_body.prop_type != 7:
            tank2.tank_body.velocity = 0, 0
        tank2.tank_body.angular_velocity = 0
        tank2.fire_available = False
        tank2.move_available = False
        tank2.rotate_available = False

        global red_win
        global green_win
        global props_num

        if props_num:
            create_prop()

        for tank in [tank1, tank2]:
            tank_shapes = tank.tank_body.shapes
            for item in tank_shapes:
                if isinstance(item, pymunk.shapes.Poly) and item in space.shapes:
                    tank.move_available = True
                if isinstance(item, pymunk.shapes.Segment) and item in space.shapes:
                    tank.fire_available = True
                if isinstance(item, pymunk.shapes.Circle) and item in space.shapes:
                    tank.rotate_available = True
            tank.update()

        if not tank1.move_available and not tank1.fire_available and not tank1.rotate_available and is_end == 0:
            green_win += 1
            is_end = 1
        if not tank2.move_available and not tank2.fire_available and not tank2.rotate_available and is_end == 0:
            red_win += 1
            is_end = 1

        # 红色坦克
        if tank1.tank_body.prop_type == 7:
            tank1.tank_body.apply_force_at_world_point(unitization(*tank1.tank_body.velocity) * -2000, (0, 0))
            if key[pygame.K_UP] and tank1.move_available:
                if math.hypot(*tank1.tank_body.velocity) <= 120:
                    tank1.tank_body.apply_force_at_world_point(tank1.tank_body.rotation_vector * 5000, (0, 0))
                if math.hypot(*tank1.tank_body.velocity) <= 80:
                    tank1.tank_body.apply_impulse_at_local_point((300, 0), (0, 0))
            if key[pygame.K_DOWN] and tank1.move_available:
                if math.hypot(*tank1.tank_body.velocity) <= 120:
                    tank1.tank_body.apply_force_at_world_point(tank1.tank_body.rotation_vector * -5000, (0, 0))
                if math.hypot(*tank1.tank_body.velocity) <= 80:
                    tank1.tank_body.apply_impulse_at_local_point((-300, 0), (0, 0))
        else:
            if key[pygame.K_UP] and tank1.move_available and game_time - tank1.col_time >= 2:
                tank1.tank_body.velocity = tank1.tank_body.rotation_vector * tank1.speed
            if key[pygame.K_DOWN] and tank1.move_available:
                tank1.tank_body.velocity = tank1.tank_body.rotation_vector * -tank1.speed

        if key[pygame.K_LEFT] and tank1.rotate_available:
            tank1.tank_body.angular_velocity = -tank1.angular_velocity
        if key[pygame.K_RIGHT] and tank1.rotate_available:
            tank1.tank_body.angular_velocity = tank1.angular_velocity

        #  绿色坦克
        if tank2.tank_body.prop_type == 7:
            tank2.tank_body.apply_force_at_world_point(unitization(*tank2.tank_body.velocity) * -2000, (0, 0))
            if key[pygame.K_w] and tank2.move_available:
                if math.hypot(*tank2.tank_body.velocity) <= 120:
                    tank2.tank_body.apply_force_at_world_point(tank2.tank_body.rotation_vector * 5000, (0, 0))
                if math.hypot(*tank2.tank_body.velocity) <= 80:
                    tank2.tank_body.apply_impulse_at_local_point((300, 0), (0, 0))
            if key[pygame.K_s] and tank2.move_available:
                if math.hypot(*tank2.tank_body.velocity) <= 120:
                    tank2.tank_body.apply_force_at_world_point(tank2.tank_body.rotation_vector * -5000, (0, 0))
                if math.hypot(*tank2.tank_body.velocity) <= 80:
                    tank2.tank_body.apply_impulse_at_local_point((-300, 0), (0, 0))
        else:
            if key[pygame.K_w] and tank2.move_available and game_time - tank2.col_time >= 2:
                tank2.tank_body.velocity = tank2.tank_body.rotation_vector * tank2.speed
            if key[pygame.K_s] and tank2.move_available:
                tank2.tank_body.velocity = tank2.tank_body.rotation_vector * -tank2.speed


        if key[pygame.K_a] and tank2.rotate_available:
            tank2.tank_body.angular_velocity = -tank2.angular_velocity
        if key[pygame.K_d] and tank2.rotate_available:
            tank2.tank_body.angular_velocity = tank2.angular_velocity

        # if key[pygame.K_KP_ENTER]:
        #     fire(space, tank1)
            # bullet.velocity = (tank1.rotation_vector) * 400

        for p in props:
            p.update()

        for item in remove_obj.copy():
            if item in space.shapes:
                space.remove(item)
        remove_obj.clear()


        for b in bullets:
            b.update(space)

        left = int(key[pygame.K_KP_4])
        up = int(key[pygame.K_KP_8])
        down = int(key[pygame.K_KP_2])
        right = int(key[pygame.K_KP_6])
        zoom_in = int(key[pygame.K_x])
        zoom_out = int(key[pygame.K_z])

        zoom_speed = 0.1
        scaling *= 1 + (zoom_speed * zoom_in - zoom_speed * zoom_out)

        translate_speed = 10
        translation = translation.translated(
            translate_speed * left - translate_speed * right,
            translate_speed * up - translate_speed * down,
        )

        draw_options.transform = (
            pymunk.Transform.scaling(scaling)
            @ translation
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if mouse_joint is not None:
                    space.remove(mouse_joint)
                    mouse_joint = None

                p = Vec2d(*event.pos)
                hit = space.point_query_nearest(p, 5, pymunk.ShapeFilter())
                if hit is not None and hit.shape.body.body_type == pymunk.Body.DYNAMIC:
                    shape = hit.shape
                    # Use the closest point on the surface if the click is outside
                    # of the shape.
                    if hit.distance > 0:
                        nearest = hit.point
                    else:
                        nearest = p
                    mouse_joint = pymunk.PivotJoint(
                        mouse_body, shape.body, (0, 0), shape.body.world_to_local(nearest)
                    )
                    mouse_joint.max_force = 50000
                    mouse_joint.error_bias = (1 - 0.15) ** 60
                    space.add(mouse_joint)

            elif event.type == pygame.MOUSEBUTTONUP:
                if mouse_joint is not None:
                    space.remove(mouse_joint)
                    mouse_joint = None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                tank1, tank2, is_end = restart(space, tank1, tank2)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                tank1, tank2, is_end = restart_train(space, tank1, tank2)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_KP_ENTER and tank1.fire_available:
                tank1.fire()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_KP_0 and tank1.tank_body.prop_type == 8 and tank1.rotate_available:
                tank1.teleport()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and tank2.fire_available:
                tank2.fire()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f and tank2.tank_body.prop_type == 8 and tank2.rotate_available:
                tank2.teleport()

            # 鼠标创造daoju
            if event.type == pygame.KEYDOWN and event.key == pygame.K_1:
                create_prop_by_mouse("gatling")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_2:
                create_prop_by_mouse("frag")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_3:
                create_prop_by_mouse("scatter")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_4:
                create_prop_by_mouse("laser")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_5:
                create_prop_by_mouse("death")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_6:
                create_prop_by_mouse("rc")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_7:
                create_prop_by_mouse("speed")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_8:
                create_prop_by_mouse("teleport")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_9:
                create_prop_by_mouse("broken")

            # 控制鼠标显示
            if event.type == pygame.KEYDOWN and event.key == pygame.K_u:
                mouse_visible = not mouse_visible
                pygame.mouse.set_visible(mouse_visible)
            # 时间静止
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                time_stop()

        if tank1.is_gatling and key[pygame.K_KP_ENTER] and tank1.fire_available:
            tank1.fire()
        if tank2.is_gatling and key[pygame.K_SPACE] and tank2.fire_available:
            tank2.fire()


        mouse_body.position = pygame.mouse.get_pos()

        draw(space, window, draw_options, line)

        space.step(dt)
        clock.tick(fps)

    pygame.quit()


if __name__ == "__main__":
    run()

