import arcade
import math

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Геннадий Александрович: учитель времени"
BUTTON1_COORDINATES = [(723, 706), (1080, 804)]
BUTTON2_COORDINATES = [(723, 586), (1080, 683)]

PLAYER_SCALE = 0.35
GRAVITY = 1.2
PLAYER_JUMP_SPEED = 20
PLAYER_MOVEMENT_SPEED = 2
PLAYER_RUN_MULTIPLIER = 3

QUICKSAND_SINK_TIME = 2

WALKING_TEXTURES = [arcade.load_texture(f"walk{i}.png") for i in range(6)]
RUNNING_TEXTURES = [arcade.load_texture(f"run{i}.png") for i in range(6)]
JUMP_TEXTURES = [arcade.load_texture(f"jump{i}.png") for i in range(2)]

STOP_POSITIONS = [
    (84, "zastavka.png", arcade.key.F1),
    (428, "quest1.png", arcade.key.F2),
    (1600, "quest2.png", arcade.key.F3),
    (2192, "quest3.png", arcade.key.F2),
    (3260, "quest4.png", arcade.key.F1),
    (3984, "quest5.png", arcade.key.F3)
]

class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background = arcade.load_texture("begin back.jpg")

    def on_draw(self):
        arcade.start_render()
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.background)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if (BUTTON1_COORDINATES[0][0] <= x <= BUTTON1_COORDINATES[1][0] and
                BUTTON1_COORDINATES[0][1] <= y <= BUTTON1_COORDINATES[1][1]):
                game_view = IntroView()
                self.window.show_view(game_view)
            elif (BUTTON2_COORDINATES[0][0] <= x <= BUTTON2_COORDINATES[1][0] and
                  BUTTON2_COORDINATES[0][1] <= y <= BUTTON2_COORDINATES[1][1]):
                arcade.close_window()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            arcade.close_window()

class IntroView(arcade.View):
    def __init__(self):
        super().__init__()
        self.intro_images = [arcade.load_texture("back1.jpg"), arcade.load_texture("upravleniye.jpg")]
        self.current_image = 0

    def on_draw(self):
        arcade.start_render()
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.intro_images[self.current_image])

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.SPACE:
            self.current_image = (self.current_image + 1) % len(self.intro_images)
            if self.current_image == 0:
                game_view = GameView()
                self.window.show_view(game_view)
        elif symbol == arcade.key.ESCAPE:
            arcade.close_window()

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.player_sprite = arcade.Sprite("ded.png", PLAYER_SCALE)
        self.player_sprite.center_x = 33
        self.player_sprite.center_y = 507

        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.gui_camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.progress = 0
        self.max_progress = 1

        self.unlocked_stop_positions = {}

        self.load_map("map.json")

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite,
            platforms=self.scene.get_sprite_list("ground"),
            gravity_constant=GRAVITY,
        )

        self.player_state = "idle"
        self.player_facing_left = False

        self.left_pressed = False
        self.right_pressed = False
        self.jump_pressed = False
        self.run_pressed = False

        self.current_walk_texture = 0
        self.current_run_texture = 0
        self.current_jump_texture = 0
        self.texture_update_time = 0.1
        self.texture_update_delta = 0

        self.dead = False

        self.in_quicksand = False
        self.quicksand_timer = 0

        self.stop_images = {stop_x: (arcade.load_texture(image_path), False) for stop_x, image_path, _ in STOP_POSITIONS}
        self.stop_image_shown = False
        self.unlock_keys_pressed = {pos[0]: False for pos in STOP_POSITIONS}
        self.current_stop_position = None

        self.player_facing_left_before_death = False

        self.current_level = 0

        self.maya_images = [arcade.load_texture("maya_response.png"), arcade.load_texture("back3.jpg"), arcade.load_texture("end.jpg")]
        self.showing_maya_images = False
        self.current_maya_image_index = 0
        self.maya_proximity_threshold = 50

    def load_map(self, map_file):
        try:
            tile_map = arcade.load_tilemap(map_file)
        except Exception as e:
            print(f"Ошибка загрузки карты: {e}")
            return

        self.scene = arcade.Scene.from_tilemap(tile_map)
        self.scene.add_sprite("Player", self.player_sprite)
        self.map_width = tile_map.width * tile_map.tile_width
        self.map_height = tile_map.height * tile_map.tile_height

        self.quicksand_list = self.scene.get_sprite_list("quicksand")
        self.mask_list = self.scene.get_sprite_list("mask")

        self.mask_start_y = SCREEN_HEIGHT - 820
        self.mask_amplitude = 5
        self.mask_period = 5
        self.mask_time = 0

        for sprite_list in [self.quicksand_list, self.mask_list]:
            for sprite in sprite_list:
                if sprite.texture:
                    sprite.set_hit_box(sprite.texture.hit_box_points)
                else:
                    print(f"Ошибка: у спрайта {sprite} отсутствует текстура")

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite,
            platforms=self.scene.get_sprite_list("ground"),
            gravity_constant=GRAVITY,
        )

        if self.progress == 1:
            self.stop_images = {stop_x: (arcade.load_texture(image_path), False) for stop_x, image_path in [
                (85, "zastavka1.png"),
                (544, "quest6.png"),
                (1248, "quest7.png"),
                (1760, "quest8.png"),
                (2500, "quest9.png"),
                (3552, "quest10.png")
            ]}
            self.stop_keys = {
                85: {'correct_key': arcade.key.F1, 'wrong_keys': []},
                544: {'correct_key': arcade.key.F1, 'wrong_keys': [arcade.key.F2, arcade.key.F3]},
                1248: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]},
                1760: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]},
                2500: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]},
                3552: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]}
            }
            self.maya_list = self.scene.get_sprite_list("maya")
        else:
            self.stop_images = {stop_x: (arcade.load_texture(image_path), False) for stop_x, image_path in [
                (84, "zastavka.png"),
                (428, "quest1.png"),
                (1600, "quest2.png"),
                (2192, "quest3.png"),
                (3260, "quest4.png"),
                (3984, "quest5.png")
            ]}
            self.stop_keys = {
                84: {'correct_key': arcade.key.F1, 'wrong_keys': []},
                428: {'correct_key': arcade.key.F2, 'wrong_keys': [arcade.key.F1, arcade.key.F3]},
                1600: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]},
                2192: {'correct_key': arcade.key.F2, 'wrong_keys': [arcade.key.F1, arcade.key.F3]},
                3260: {'correct_key': arcade.key.F1, 'wrong_keys': [arcade.key.F2, arcade.key.F3]},
                3984: {'correct_key': arcade.key.F3, 'wrong_keys': [arcade.key.F1, arcade.key.F2]}
            }

        self.unlocked_stop_positions.clear()
        for stop_x in self.stop_images.keys():
            self.unlocked_stop_positions[stop_x] = False

    def on_draw(self):
        arcade.start_render()
        self.camera.use()
        self.scene.draw()

        if not self.in_quicksand:
            self.player_sprite.draw()

        text_position_x = 30
        text_position_y = SCREEN_HEIGHT - 80

        self.gui_camera.use()

        image = arcade.load_texture("fullmask1.png")
        arcade.draw_lrwh_rectangle_textured(text_position_x + 95, text_position_y - 10, image.width * 1.5,
                                            image.height * 1.5, image)

        arcade.draw_text(f"{self.progress} / {self.max_progress}", text_position_x, text_position_y,
                         arcade.color.ANTIQUE_WHITE, 22, font_name="8BIT WONDER(RUS BY LYAJKA)")

        if self.dead:
            arcade.draw_lrtb_rectangle_filled(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0,
                                              arcade.make_transparent_color(arcade.color.BLACK, 128))

            arcade.draw_text('НАЖМИТЕ "R" И НАЧИНАЙТЕ ЗАНОВО', SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                             arcade.color.ANTIQUE_WHITE, 32, anchor_x="center",
                             font_name="8BIT WONDER(RUS BY LYAJKA)")

        for stop_x, (image, _) in self.stop_images.items():
            if self.stop_image_shown and stop_x == self.current_stop_position:
                arcade.draw_lrwh_rectangle_textured(
                    SCREEN_WIDTH // 2 - image.width // 2,
                    SCREEN_HEIGHT // 2 - image.height // 2,
                    image.width, image.height,
                    image
                )

        if self.showing_maya_images:
            current_image = self.maya_images[self.current_maya_image_index]
            if self.current_maya_image_index == 0:
                arcade.draw_texture_rectangle(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, current_image.width,
                                              current_image.height, current_image)
            else:
                arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, current_image)

    def on_key_press(self, symbol, modifiers):
        if self.showing_maya_images:
            if symbol == arcade.key.SPACE:
                if self.current_maya_image_index < len(self.maya_images) - 1:
                    self.current_maya_image_index += 1
            elif symbol == arcade.key.ESCAPE:
                if self.current_maya_image_index == len(self.maya_images) - 1:
                    arcade.close_window()
                else:
                    self.showing_maya_images = False
                    self.current_maya_image_index = 0
            return

        if symbol == arcade.key.LEFT or symbol == arcade.key.A:
            self.left_pressed = True
            self.player_state = "walk"
            self.player_facing_left = True
        elif symbol == arcade.key.RIGHT or symbol == arcade.key.D:
            self.right_pressed = True
            self.player_state = "walk"
            self.player_facing_left = False
        elif symbol == arcade.key.W or symbol == arcade.key.UP:
            if self.physics_engine.can_jump() and not self.in_quicksand:
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                self.player_state = "jump"
        elif symbol == arcade.key.LSHIFT or symbol == arcade.key.RSHIFT:
            self.run_pressed = True
            self.player_state = "run"
        elif symbol == arcade.key.R and self.dead:
            self.respawn_player()
        elif symbol == arcade.key.R:
            self.respawn_player()
        elif symbol == arcade.key.ESCAPE:
            arcade.close_window()

        if self.current_stop_position is not None:
            stop_info = self.stop_keys[self.current_stop_position]
            if symbol == stop_info['correct_key']:
                if not self.dead:
                    self.stop_images[self.current_stop_position] = (
                        self.stop_images[self.current_stop_position][0], False)
                    self.stop_image_shown = False
                    self.unlocked_stop_positions[
                        self.current_stop_position] = True
                    self.current_stop_position = None
                    self.player_sprite.center_x += 1
            elif symbol in stop_info['wrong_keys']:
                if not self.dead:
                    self.dead = True
                    self.stop_image_shown = False
                    self.current_stop_position = None

    def on_key_release(self, symbol, modifiers):
        if symbol == arcade.key.LEFT or symbol == arcade.key.A:
            self.left_pressed = False
            if not self.right_pressed:
                self.player_state = "idle"
        elif symbol == arcade.key.RIGHT or symbol == arcade.key.D:
            self.right_pressed = False
            if not self.left_pressed:
                self.player_state = "idle"
        elif symbol == arcade.key.LSHIFT or symbol == arcade.key.RSHIFT:
            self.run_pressed = False
            if not self.left_pressed and not self.right_pressed:
                self.player_state = "idle"

        for stop_x, _, close_key in STOP_POSITIONS:
            if symbol == close_key:
                self.unlock_keys_pressed[stop_x] = False

    def on_update(self, delta_time):
        if self.dead:
            return

        self.physics_engine.update()

        if self.player_sprite.center_y < 0:
            self.player_state = "idle"
            self.dead = True
            self.player_facing_left_before_death = self.player_facing_left

        if not self.stop_image_shown:
            if self.left_pressed and not self.right_pressed:
                self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
                if self.run_pressed:
                    self.player_sprite.change_x *= PLAYER_RUN_MULTIPLIER
                self.player_facing_left = True
            elif self.right_pressed and not self.left_pressed:
                self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
                if self.run_pressed:
                    self.player_sprite.change_x *= PLAYER_RUN_MULTIPLIER
                self.player_facing_left = False
            else:
                self.player_sprite.change_x = 0

        self.player_sprite.center_x = max(0, min(self.player_sprite.center_x, self.map_width))
        self.player_sprite.center_y = max(0, min(self.player_sprite.center_y, self.map_height))

        valid_quicksand_sprites = arcade.SpriteList()
        for sprite in self.quicksand_list:
            if sprite.get_hit_box() and all(vertex is not None for vertex in sprite.get_hit_box()):
                valid_quicksand_sprites.append(sprite)

        if arcade.check_for_collision_with_list(self.player_sprite, valid_quicksand_sprites):
            if not self.in_quicksand:
                self.in_quicksand = True
                self.quicksand_timer = QUICKSAND_SINK_TIME
        else:
            self.in_quicksand = False

        if self.quicksand_list and all(sprite.texture for sprite in self.quicksand_list):
            if arcade.check_for_collision_with_list(self.player_sprite, self.quicksand_list):
                if not self.in_quicksand:
                    self.in_quicksand = True
                    self.quicksand_timer = QUICKSAND_SINK_TIME
        else:
            self.in_quicksand = False

        if self.in_quicksand:
            self.sink_in_quicksand(delta_time)

        if self.physics_engine.can_jump() and self.player_state == "jump":
            self.player_state = "idle"

        self.animate_player()
        self.scroll_to_player()
        self.check_stop_positions()

        found_stop_position = False
        player_x = self.player_sprite.center_x
        for stop_x in self.stop_keys.keys():
            if abs(player_x - stop_x) < 50:
                found_stop_position = True
                if stop_x in self.unlocked_stop_positions:
                    if not self.stop_image_shown and not self.unlocked_stop_positions[stop_x]:
                        self.current_stop_position = stop_x
                        self.stop_images[stop_x] = (self.stop_images[stop_x][0], True)
                        self.stop_image_shown = True
                break

        if not found_stop_position and self.current_stop_position is not None:
            if self.current_stop_position in self.stop_images:
                self.stop_images[self.current_stop_position] = (self.stop_images[self.current_stop_position][0], False)
                self.stop_image_shown = False
                self.current_stop_position = None

        if self.stop_image_shown:
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

        self.mask_time += delta_time
        mask_y_offset = self.mask_amplitude * math.sin(2 * math.pi * self.mask_time / self.mask_period)
        for mask in self.mask_list:
            mask.top = self.mask_start_y + mask_y_offset

        for mask_sprite in self.mask_list:
            if arcade.check_for_collision(self.player_sprite, mask_sprite):
                if self.progress == 0:
                    self.load_second_level(start_x=33, start_y=507)

        if self.progress == 1:
            maya_list = self.scene.get_sprite_list("maya")
            for maya_sprite in maya_list:
                if abs(self.player_sprite.center_x - maya_sprite.center_x) < self.maya_proximity_threshold:
                    self.showing_maya_images = True
                    break

        if not found_stop_position and self.current_stop_position is not None:
            if self.current_stop_position in self.unlocked_stop_positions:
                if not self.stop_image_shown and not self.unlocked_stop_positions[self.current_stop_position]:
                    self.stop_images[self.current_stop_position] = (
                        self.stop_images[self.current_stop_position][0], False)
                    self.stop_image_shown = False
                    self.current_stop_position = None

    def load_second_level(self, start_x, start_y):
        self.progress = 1
        self.load_map("map1.json")
        self.player_sprite.center_x = start_x
        self.player_sprite.center_y = start_y

    def check_stop_positions(self):
        def check_stop_positions(self):
            player_x = self.player_sprite.center_x
            player_facing_left = self.player_sprite.change_x < 0
            if self.current_stop_position is not None:
                stop_x, _, _ = STOP_POSITIONS[self.current_stop_position]
                if player_x < stop_x and not player_facing_left:
                    self.stop_image_shown = False
                    self.current_stop_position = None
            else:
                for stop_x, _, _ in STOP_POSITIONS:
                    if abs(player_x - stop_x) < 50:
                        if player_facing_left:
                            self.current_stop_position = STOP_POSITIONS.index((stop_x, _, _))
                            self.stop_image_shown = True
                        return
            self.stop_image_shown = False

    def show_stop_image(self, stop_x, image_path):
        if stop_x not in self.stop_images:
            image = arcade.load_texture(image_path)
            self.stop_images[stop_x] = (image, True)

    def hide_all_stop_images(self):
        for stop_x in self.stop_images:
            self.stop_images[stop_x] = (self.stop_images[stop_x][0], False)

    def sink_in_quicksand(self, delta_time):
        if self.quicksand_timer > 0:
            self.quicksand_timer -= delta_time
            self.player_sprite.change_y = 1
            self.left_pressed = False
            self.right_pressed = False
            self.jump_pressed = False
            self.run_pressed = False
            self.player_sprite.change_x = 0
            self.player_state = "idle"
        else:
            self.dead = True
            self.player_facing_left_before_death = self.player_facing_left

    def animate_player(self):
        self.texture_update_delta += 1 / 60

        if self.player_state == "idle":
            self.player_sprite.texture = arcade.load_texture("ded.png", flipped_horizontally=self.player_facing_left)
        elif self.player_state == "walk":
            if self.texture_update_delta >= self.texture_update_time:
                self.texture_update_delta = 0
                self.current_walk_texture = (self.current_walk_texture + 1) % len(WALKING_TEXTURES)
            texture = WALKING_TEXTURES[self.current_walk_texture]
            self.player_sprite.texture = arcade.load_texture(texture.name, flipped_horizontally=self.player_facing_left)
        elif self.player_state == "jump":
            if self.texture_update_delta >= self.texture_update_time:
                self.texture_update_delta = 0
                self.current_jump_texture = (self.current_jump_texture + 1) % len(JUMP_TEXTURES)
            texture = JUMP_TEXTURES[self.current_jump_texture]
            self.player_sprite.texture = arcade.load_texture(texture.name, flipped_horizontally=self.player_facing_left)
        elif self.player_state == "run":
            if self.texture_update_delta >= self.texture_update_time:
                self.texture_update_delta = 0
                self.current_run_texture = (self.current_run_texture + 1) % len(RUNNING_TEXTURES)
            texture = RUNNING_TEXTURES[self.current_run_texture]
            self.player_sprite.texture = arcade.load_texture(texture.name, flipped_horizontally=self.player_facing_left)

    def respawn_player(self):
        self.player_sprite.center_x = 33
        self.player_sprite.center_y = 507
        self.dead = False
        self.stop_image_shown = False
        self.current_stop_position = None

        if arcade.check_for_collision_with_list(self.player_sprite, self.quicksand_list):
            self.in_quicksand = True
            self.quicksand_timer = QUICKSAND_SINK_TIME
        else:
            self.in_quicksand = False
            self.quicksand_timer = 0
        self.player_facing_left = self.player_facing_left_before_death
        self.player_state = "idle"
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0

    def scroll_to_player(self):
        screen_center_x = self.player_sprite.center_x - (self.camera.viewport_width / 2)
        screen_center_y = self.player_sprite.center_y - (self.camera.viewport_height / 2)
        screen_center_x = max(0, min(screen_center_x, self.map_width - self.camera.viewport_width))
        screen_center_y = max(0, min(screen_center_y, self.map_height - self.camera.viewport_height))

        self.camera.move_to((screen_center_x, screen_center_y), 0.1)

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()

if __name__ == "__main__":
    main()
