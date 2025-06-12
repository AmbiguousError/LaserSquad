import pygame
import settings

def draw_home_screen(game):
    game.screen.fill(settings.COLOR_DARK_GRAY)
    title_text = game.FONT_L.render("Tactical Squad Game", True, settings.COLOR_WHITE)
    title_rect = title_text.get_rect(center=(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2 - 200))
    game.screen.blit(title_text, title_rect)
    instructions = ["INSTRUCTIONS", "", "Select Unit: Left-Click or Press Keys 1-4", "Move Unit: Right-Click on a valid floor tile",
                    "Attack: Right-Click on a visible enemy", "Melee: Right-Click an ADJACENT enemy", "Heal: Press 'H' or Click Heal Button",
                    "Posture: Press 'C' to toggle Stand/Prone (1 AP)", "Overwatch: Click button or Press 'O' (3 AP)", "End Turn: Click the End Turn button",
                    "Scroll Map: Arrow Keys or move mouse to screen edge", "Jump to Map Location: Click on the minimap", "", "Press any key to start..."]
    for i, line in enumerate(instructions):
        line_text = game.FONT_M.render(line, True, settings.COLOR_WHITE)
        line_rect = line_text.get_rect(center=(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2 - 80 + i * 25))
        game.screen.blit(line_text, line_rect)

def draw_game_world(game):
    game.game_surface.fill(settings.COLOR_BLACK)
    game_time = pygame.time.get_ticks()
    game.game_map.draw(game.game_surface, game.camera)
    for unit in game.player_squad + game.all_enemies:
        unit.draw(game.game_surface, game.camera, game.FONT_S, game_time)
    if game.selected_unit: game.selected_unit.draw_path(game.game_surface, game.camera)
    for start, end, timer in game.laser_effects:
        start_pos = game.camera.apply_coords(start[0], start[1]); end_pos = game.camera.apply_coords(end[0], end[1])
        start_center = (start_pos[0] + settings.TILE_SIZE // 2, start_pos[1] + settings.TILE_SIZE // 2)
        end_center = (end_pos[0] + settings.TILE_SIZE // 2, end_pos[1] + settings.TILE_SIZE // 2)
        pygame.draw.line(game.game_surface, settings.COLOR_LASER, start_center, end_center, 3)
    for msg in game.skill_check_messages:
        pos_x, pos_y = game.camera.apply_coords(msg['pos'][0], msg['pos'][1])
        text = game.FONT_M.render(msg['text'], True, msg['color'])
        alpha = int(255 * (msg['timer'] / 60)); text.set_alpha(alpha)
        text_rect = text.get_rect(center=(pos_x + settings.TILE_SIZE // 2, pos_y - 20))
        game.game_surface.blit(text, text_rect)
    game.screen.blit(game.game_surface, (settings.SIDE_PANEL_WIDTH, 0))
    draw_squad_ui(game); draw_bottom_ui(game)
    if game.game_state == 'GAME_OVER': draw_game_over(game)
    
def draw_game_over(game):
    overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180));
    text = game.FONT_L.render(game.game_over_message, True, settings.COLOR_WHITE)
    text_rect = text.get_rect(center=(settings.SCREEN_WIDTH/2, settings.SCREEN_HEIGHT/2 - 150))
    overlay.blit(text, text_rect)
    awards = []
    if any(u.kills > 0 for u in game.player_squad):
        killer = max(game.player_squad, key=lambda u: u.kills)
        if killer.kills > 0: awards.append(f"Commando: {killer.name} ({killer.kills} kills)")
    if any(u.distance_travelled > 0 for u in game.player_squad):
        runner = max(game.player_squad, key=lambda u: u.distance_travelled)
        if runner.distance_travelled > 0: awards.append(f"Marathoner: {runner.name} ({int(runner.distance_travelled)}m)")
    if any(u.heals_given > 0 for u in game.player_squad):
        medic = max(game.player_squad, key=lambda u: u.heals_given)
        if medic.heals_given > 0: awards.append(f"Medic: {medic.name} ({medic.heals_given} heals)")
    best_marksman = None; best_accuracy = -1
    for u in game.player_squad:
        if u.shots_taken > 0:
            accuracy = u.shots_hit / u.shots_taken
            if accuracy >= best_accuracy: best_accuracy = accuracy; best_marksman = u
    if best_marksman: awards.append(f"Marksman: {best_marksman.name} ({best_accuracy:.0%})")
    y_offset = settings.SCREEN_HEIGHT/2 - 80
    if awards:
        award_title_text = game.FONT_M.render("--- AWARDS ---", True, settings.COLOR_WHITE)
        award_title_rect = award_title_text.get_rect(center=(settings.SCREEN_WIDTH/2, y_offset))
        overlay.blit(award_title_text, award_title_rect)
        y_offset += 40
        for i, award_str in enumerate(awards):
            award_text = game.FONT_M.render(award_str, True, settings.COLOR_LASER)
            award_rect = award_text.get_rect(center=(settings.SCREEN_WIDTH/2, y_offset + i * 30))
            overlay.blit(award_text, award_rect)
    prompt_text = game.FONT_M.render("Press any key to return to the main menu.", True, settings.COLOR_WHITE)
    prompt_rect = prompt_text.get_rect(center=(settings.SCREEN_WIDTH/2, settings.SCREEN_HEIGHT - 150))
    overlay.blit(prompt_text, prompt_rect)
    game.screen.blit(overlay, (0,0))

def draw_squad_ui(game):
    panel_rect = pygame.Rect(0, 0, settings.SIDE_PANEL_WIDTH, settings.SCREEN_HEIGHT)
    pygame.draw.rect(game.screen, settings.COLOR_UI_BG, panel_rect)
    pygame.draw.rect(game.screen, settings.COLOR_UI_BORDER, panel_rect, 2)
    start_y = 20
    for unit in game.player_squad:
        box_height = 100 # Increased height for AP bar
        unit_box_rect = pygame.Rect(10, start_y, settings.SIDE_PANEL_WIDTH - 20, box_height)
        box_color = (40, 40, 70) if unit.is_selected else settings.COLOR_DARK_GRAY
        pygame.draw.rect(game.screen, box_color, unit_box_rect, border_radius=5)
        pygame.draw.rect(game.screen, settings.COLOR_UI_BORDER, unit_box_rect, 1, border_radius=5)
        name_text = game.FONT_M.render(f"{unit.number}. {unit.name}", True, settings.COLOR_WHITE)
        game.screen.blit(name_text, (20, start_y + 5))
        hp_text = game.FONT_S.render(f"HP: {unit.hp}/{settings.UNIT_MAX_HP}", True, settings.COLOR_PLAYER_LIGHT)
        game.screen.blit(hp_text, (20, start_y + 30))
        ap_text = game.FONT_S.render(f"AP: {unit.ap}/{settings.UNIT_MAX_AP}", True, settings.COLOR_PLAYER_LIGHT)
        game.screen.blit(ap_text, (120, start_y + 30))

        # --- NEW: AP Bar ---
        ap_bar_width = settings.SIDE_PANEL_WIDTH - 40
        ap_bar_height = 10
        ap_bar_x = 20
        ap_bar_y = start_y + 75
        
        ap_percent = unit.ap / settings.UNIT_MAX_AP
        current_ap_width = ap_bar_width * ap_percent
        
        pygame.draw.rect(game.screen, settings.COLOR_DARK_GRAY, (ap_bar_x, ap_bar_y, ap_bar_width, ap_bar_height))
        pygame.draw.rect(game.screen, settings.COLOR_PLAYER_LIGHT, (ap_bar_x, ap_bar_y, current_ap_width, ap_bar_height))
        pygame.draw.rect(game.screen, settings.COLOR_UI_BORDER, (ap_bar_x, ap_bar_y, ap_bar_width, ap_bar_height), 1)

        if not unit.is_alive: status_text = game.FONT_M.render("KIA", True, settings.COLOR_ENEMY)
        elif unit.is_on_overwatch: status_text = game.FONT_M.render("Overwatch", True, settings.COLOR_OVERWATCH)
        elif unit.posture == 'prone': status_text = game.FONT_M.render("Prone", True, settings.COLOR_GRAY)
        else: status_text = None
        if status_text: game.screen.blit(status_text, (20, start_y + 50))
        start_y += box_height + 10

def draw_minimap(game):
    game.minimap_surface.fill(settings.COLOR_UI_BG)
    for x in range(game.game_map.width):
        for y in range(game.game_map.height):
            if game.game_map.tiles[x][y].is_explored:
                color = settings.COLOR_WALL if game.game_map.tiles[x][y].is_wall else settings.COLOR_FLOOR_EXPLORED
                if game.game_map.tiles[x][y].is_cover: color = settings.COLOR_GRAY if game.game_map.tiles[x][y].is_visible else settings.COLOR_DARK_GRAY
                pygame.draw.rect(game.minimap_surface, color, (x*settings.MINIMAP_SCALE, y*settings.MINIMAP_SCALE, settings.MINIMAP_SCALE, settings.MINIMAP_SCALE))
    for unit in game.player_squad + game.all_enemies:
        if unit.is_alive and game.game_map.tiles[unit.x][unit.y].is_visible:
            color = settings.COLOR_PLAYER_LIGHT if unit.team == 'player' else settings.COLOR_ENEMY_LIGHT
            pygame.draw.rect(game.minimap_surface, color, (unit.x*settings.MINIMAP_SCALE, unit.y*settings.MINIMAP_SCALE, settings.MINIMAP_SCALE, settings.MINIMAP_SCALE))
    pygame.draw.rect(game.minimap_surface, settings.COLOR_UI_BORDER, game.minimap_surface.get_rect(), 2)
    game.screen.blit(game.minimap_surface, game.minimap_rect)

def draw_bottom_ui(game):
    ui_panel = pygame.Rect(0, settings.SCREEN_HEIGHT - 100, settings.SCREEN_WIDTH, 100)
    pygame.draw.rect(game.screen, settings.COLOR_UI_BG, ui_panel); pygame.draw.rect(game.screen, settings.COLOR_UI_BORDER, ui_panel, 2)
    turn_text_str = f"Turn {game.turn_number}: {game.game_state.replace('_', ' ')}"; turn_text = game.FONT_M.render(turn_text_str, True, settings.COLOR_WHITE)
    game.screen.blit(turn_text, (settings.SIDE_PANEL_WIDTH + 20, settings.SCREEN_HEIGHT - 85))
    
    enemies_left = len([u for u in game.all_enemies if u.is_alive])
    enemy_text = game.FONT_M.render(f"Enemies Remaining: {enemies_left}", True, settings.COLOR_WHITE)
    game.screen.blit(enemy_text, (settings.SIDE_PANEL_WIDTH + 20, settings.SCREEN_HEIGHT - 45))

    mouse_pos = pygame.mouse.get_pos()
    
    # End Turn Button
    button_color = settings.COLOR_BUTTON_HOVER if game.end_turn_button.collidepoint(mouse_pos) else settings.COLOR_BUTTON
    pygame.draw.rect(game.screen, button_color, game.end_turn_button, border_radius=5)
    button_text = game.FONT_M.render("End Turn", True, settings.COLOR_BUTTON_TEXT)
    text_rect = button_text.get_rect(center=game.end_turn_button.center); game.screen.blit(button_text, text_rect)
    
    # Overwatch Button
    can_overwatch = game.selected_unit and game.selected_unit.ap >= settings.OVERWATCH_COST and not game.selected_unit.is_on_overwatch
    button_color = settings.COLOR_BUTTON_HOVER if game.overwatch_button.collidepoint(mouse_pos) and can_overwatch else settings.COLOR_BUTTON
    pygame.draw.rect(game.screen, button_color, game.overwatch_button, border_radius=5)
    text_color = settings.COLOR_BUTTON_TEXT if can_overwatch else settings.COLOR_GRAY
    button_text = game.FONT_M.render("Overwatch", True, text_color)
    text_rect = button_text.get_rect(center=game.overwatch_button.center); game.screen.blit(button_text, text_rect)
    
    # Prone Button
    prone_text = "Stand" if game.selected_unit and game.selected_unit.posture == 'prone' else "Prone"
    can_change_posture = game.selected_unit and game.selected_unit.ap >= settings.POSTURE_CHANGE_COST
    button_color = settings.COLOR_BUTTON_HOVER if game.prone_button.collidepoint(mouse_pos) and can_change_posture else settings.COLOR_BUTTON
    pygame.draw.rect(game.screen, button_color, game.prone_button, border_radius=5)
    text_color = settings.COLOR_BUTTON_TEXT if can_change_posture else settings.COLOR_GRAY
    button_text = game.FONT_M.render(prone_text, True, text_color)
    text_rect = button_text.get_rect(center=game.prone_button.center); game.screen.blit(button_text, text_rect)

    # Heal Button
    can_heal = game.can_selected_unit_heal()
    button_color = settings.COLOR_BUTTON_HOVER if game.heal_button.collidepoint(mouse_pos) and can_heal else settings.COLOR_BUTTON
    pygame.draw.rect(game.screen, button_color, game.heal_button, border_radius=5)
    text_color = settings.COLOR_BUTTON_TEXT if can_heal else settings.COLOR_GRAY
    button_text = game.FONT_M.render("Heal", True, text_color)
    text_rect = button_text.get_rect(center=game.heal_button.center); game.screen.blit(button_text, text_rect)


    draw_minimap(game)
