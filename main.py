########## from __authors__ import Jeanne Cazelais et Junyi Zhang ##########

#############################
########## IMPORTS ##########
#############################

from __future__ import annotations
import math
import random

from graphelib import Graphe, Sommet
from pilefile import Pile, File
import turtle

from data import green_raw, orange_raw, blue_raw, yellow_raw

#####################################
####### BASIC VARIABLES SETUP #######
#####################################

turtle.tracer(0, 0)  # no forced delay before each frame

# Create "game" states
ALL_GAME_STATES = {
    "INTRO": "intro",
    "ASK_ORIGIN": "ask_origin",
    "ASK_DESTINATION": "ask_destination",
    "ANIMATE": "animate",
    "END": "end",
}
GAME_STATE = ALL_GAME_STATES["INTRO"]

# * GAME VARIABLES
ORIGIN_COORD: tuple[float, float] = (0, 0)  # coords of the origin
ORIGIN: Sommet | str = ""  # Sommet object of the origin
DESTINATION: Sommet | str = ""  # Sommet object of the destination
ROUTE: File = File()  # all the metro stations the play has to go through


# * CREATE STM GRAPHE
def create_graph(data: list, system: Graphe):
    """Ajoute une selection d'information raw à un graphe mutable donné"""
    for i in range(len(data) - 1):
        if not data[i]["distance_to_next_station"]:
            continue
        system.ajouteArete(
            data[i]["name"],
            data[i + 1]["name"],
            data[i]["distance_to_next_station"],
        )


STM_RAW = green_raw[:]
STM_RAW.extend(orange_raw)
STM_RAW.extend(blue_raw)
STM_RAW.extend(yellow_raw)

STM = Graphe(oriente=False)
create_graph(STM_RAW, STM)
GREEN = Graphe(oriente=False)
create_graph(green_raw, GREEN)
ORANGE = Graphe(oriente=False)
create_graph(orange_raw, ORANGE)
BLUE = Graphe(oriente=False)
create_graph(blue_raw, BLUE)
LINES = {
    'orange': ORANGE,
    'verte': GREEN,
    'bleue': BLUE
}
# jaune est skippé — les sous-graphes sont utilisés pour traiter si le joueur peut rester sur la même ligne


# * Initial screen setup
SCREEN_SIZE = 640
screen = turtle.Screen()
screen.title("STM Simulator in a perfect world")
screen.setup(width=SCREEN_SIZE, height=SCREEN_SIZE)
try:
    screen.cv._rootwindow.resizable(False, False)  # (hopefully) lock window size in place
except AttributeError:
    print("Could not lock window ratio.")

# Add STM map as turtle object ;)
screen.addshape("stm.gif")
screen.addshape("stmBig.gif")
BG_RATIO = 1536 / 640


#################################
######### CLASSES SETUP #########
#################################

# * Create User/Player/Train/ykwim
class User(turtle.Turtle):
    def __init__(self, color):
        # create turtle object
        super().__init__("circle", visible=False)
        # self variables
        self._speed = 0
        self._destination = (0, 0)
        self._pos = (0, 0)
        # turtle variables
        self.color(color)
        self.speed = 10
        self.penup()
        self.goto(self._pos)

    def loop(self, stations_left_in_queue):
        """Animate the player for ONE FRAME"""
        self.shapesize(BG_RATIO)  # set bigger player size if not done already

        # slow down if arriving soon, otherwise accelerate
        if stations_left_in_queue <= 5:
            self._speed = max(self._speed - 0.2, 2.5)
        else:
            self._speed = min(self._speed + 0.1, 6)

        # decompose & set next position
        tx, ty = self._destination
        x, y = self._pos
        distance = math.dist(self._destination, self._pos)
        nx = self._speed * (tx - x) / (distance + 0.0001) + x
        ny = self._speed * (ty - y) / (distance + 0.0001) + y
        # set position relative to camera
        self.goto(*map(lambda m, s: s * BG_RATIO + m, bg.get_coord(), (nx, ny)))

        # if sub-destination will be reached in 3/2 frames, change destination to next one in queue (by returning T/F)
        if distance <= self._speed * 1.5:
            self._pos = (tx, ty)
            if stations_left_in_queue == 1:
                # reset speed if arriving at final destination
                self._speed = 0
            return True
        else:
            self._pos = (nx, ny)
            return False

    def get_coord(self):
        """Return the displayed coordinates of the player"""
        return self._pos

    def set_destination(self, target):
        """Set new destination of the player through sommet"""
        coord = get_coord_from_sommet(target)
        self._destination = tuple(c * SCREEN_SIZE for c in coord)

    def set_destination_from_coord(self, coord):
        """Set new destination of the player directly through a coordinate"""
        self._destination = coord

    def teleport_to_destination(self):
        """Teleport to destination (duh)"""
        self._pos = self._destination
        self.goto(*self._destination)

    def reset_after_animation(self):
        """Teleport to final position and reset size after animation"""
        self.goto(*self._pos)
        self.shapesize(1)


# * Create dynamic map swapper
class BG:
    def __init__(self, normal_map: turtle.Turtle, dynamic_map: turtle.Turtle):
        self._normal_map = normal_map
        self._normal_map.penup()
        self._normal_map.hideturtle()

        self._dynamic_map = dynamic_map
        self._dynamic_map.penup()
        self._dynamic_map.hideturtle()

        self._current_is_dynamic = False
        self._coord = (0, 0)

    def set_dynamic_map(self):
        """Dynamically swap to dynamic map (the zoomed-in one)"""
        self._normal_map.hideturtle()
        self._dynamic_map.showturtle()
        self._current_is_dynamic = True

    def set_normal_map(self):
        """Dynamically swap to normal map (the non-zoomed-in one)"""
        self._normal_map.showturtle()
        self._dynamic_map.hideturtle()
        self._current_is_dynamic = False

    def follow_user(self, coord):
        """Dynamically update follow camera xy positions"""
        if not self._current_is_dynamic:
            return
        self._coord = tuple(map(lambda s, n: s * 0.8 + n * 0.2, self._coord, coord))
        self._dynamic_map.goto(*self._coord)

    def get_coord(self):
        """Return the follow camera's coordinates"""
        return self._coord

    def reset_follow_cam_position(self):
        """Reset the follow camera's position"""
        self._dynamic_map.goto(0, 0)
        self._coord = (0, 0)


# * Super confetti
class Confetti(turtle.Turtle):
    def __init__(self, i):
        super().__init__("circle")
        self._is_left_side = i % 2 == 0
        # turtle properties
        self.penup()
        self.shapesize(0.5)
        self.color(random.choice(["red", "blue", "green", "yellow", "purple", "orange"]))
        # confetti setup
        self._x = 0
        self._y = 0
        self._vx = 0
        self._vy = 0
        self._delay = 0
        self.reset()

    def reset(self):
        """Reset confetti to be offscreen and ready to be shot"""
        half = SCREEN_SIZE // 2
        margin = 16

        self._x = (half + margin) * (-1 if self._is_left_side else 1)
        self._y = random.random() * half * 2 - half
        self._vx = random.random() * (15 if self._is_left_side else -15)
        self._vy = random.random() * 5 + 5
        self._delay = random.random() * 30

        self.goto(self._x, self._y)

    def animate(self):
        """Animate confetti FOR ONE FRAME"""
        if self._delay > 0:
            # wait until delay is cleared before shooting this confetti
            self._delay -= 1
            return

        self._x += self._vx
        self._y += self._vy
        self._vy -= 0.4

        self.goto(self._x, self._y)


class ConfettiGroup:
    def __init__(self):
        self._all_confettis = [Confetti(i) for i in range(60)]

    def animate(self):
        """Animate all confettis for one frame"""
        for t in self._all_confettis:
            t.animate()

    def reset(self):
        """Reset all confettis"""
        for t in self._all_confettis:
            t.reset()


class Label(turtle.Turtle):
    def __init__(self):
        super().__init__(visible=False)
        self.penup()

    def print(self, text, *coord, erase=True):
        if erase:
            self.clear()
        self.goto(*coord)
        self.write(text, align='center', font=('Arial', 16, 'bold'))


class IntroButton(turtle.Turtle):
    ALL_STATES = {
        'pulse': 'PULSE',
        'grow': 'GROW',
        'shrink': 'SHRINK',
        'inactive': 'INACTIVE'
    }

    def __init__(self):
        super().__init__("triangle")
        self.color("white")
        self.shapesize(3)

        self._pulse_count = 0
        self._pulse_size = 0
        self._old_pulse_size = 0
        self.state = self.ALL_STATES['pulse']  # PUBLIC variable

    def pulse(self):
        """Make the button's background slowly pulse"""
        self._pulse_count += math.pi / 40
        self._old_pulse_size = self._pulse_size
        self._pulse_size = int(16 * math.sin(self._pulse_count) + 144)
        self.clear()
        self.dot(self._pulse_size, 'black')

    def grow(self):
        """Grow the background circle to fill the screen"""
        self._pulse_size += max((self._pulse_size - self._old_pulse_size) / 5, 0.5)
        self.clear()
        self.dot(self._pulse_size, 'black')

        if self._pulse_size > SCREEN_SIZE * 3:
            self.state = self.ALL_STATES['shrink']
            return True
        return False

    def shrink(self):
        """Shrink the grown circle to reveal the game"""
        self._pulse_size -= max(self._pulse_size / 5, 0.5)
        if self._pulse_size <= 0:
            return True

        self.clear()
        self.dot(self._pulse_size, 'black')
        rgb = min(max(self._pulse_size / 4 - 192, 0), 255) / 255
        self.color(rgb, rgb, rgb)

        if rgb == 0:
            self.hideturtle()

        return False


user = User("#1bcdd0")
confetti = ConfettiGroup()
label = Label()
intro_button = IntroButton()
bg = BG(turtle.Turtle("stm.gif", visible=False), turtle.Turtle("stmBig.gif", visible=False))


######################################
######## OFTEN-USED FUNCTIONS ########
######################################

def dijkstra(g: Graphe, start: Sommet, end: Sommet):
    """A polished version of the Dijkstra algorithm"""
    unvisited: set[Sommet] = set(g.listeSommets())  # Un set de sommets qui reste à visiter
    distance_to = {s: {"w": math.inf, "p": []} for s in unvisited}  # Le poids et les chemins à traverser par sommet
    distance_to[start]["w"] = 0  # Set le poids du point de départ à zéro
    while len(unvisited) > 0:
        nearest = min(unvisited, key=lambda e: distance_to[e]["w"])  # Prendre le sommet le plus proche
        unvisited.remove(nearest)  # Enlever ce sommet du set des sommets à visiter
        for b in set(nearest.listeVoisins()) & unvisited:  # Itérer dans tous les voisins non-visités
            new_distance = distance_to[nearest]["w"] + nearest.poids(b)  # Nouvelle distance à partir de ce point
            if new_distance < distance_to[b]["w"]:
                # Si la nouvelle distance est plus petite que l'ancienne, la remplacer
                distance_to[b]["w"] = new_distance  # Explications détaillées : https://youtu.be/dQw4w9WgXcQ
                distance_to[b]["p"] = distance_to[nearest]["p"] + [nearest]
    # Ajouter la destination node au chemin le plus court et retourner le chemin et le weight
    distance_to[end]["p"].append(end)
    return distance_to[end]


def closest_station(coord: tuple):
    """Prend en paramètre les coordonnées de l'emplacement de l'utilisateur et retourne la station la plus proche en considérant les rives"""
    dist_min = math.inf
    station = ""
    x = coord[0]
    y = coord[1]
    riviere_des_prairies = 0.5 * x + 310  # approximation de la Rivière-des-Prairies
    fleuve_saint_laurent = 2 * x - 400  # approximation du fleuve Saint-Laurent

    if y > riviere_des_prairies:  # si on est à Laval
        for dictio in STM_RAW[54:57]:  # on itère sur les trois stations à Laval seulement
            candidat = (dictio["x"] * SCREEN_SIZE, dictio["y"] * SCREEN_SIZE)
            if math.dist(coord, candidat) < dist_min:  # si la distance est plus petite que précédemment
                dist_min = math.dist(coord, candidat)
                station = dictio["name"]
    elif y < fleuve_saint_laurent:  # île Sainte-Hélène ou rive sud
        jean_drapeau_x = STM_RAW[-2]["x"] * SCREEN_SIZE
        jean_drapeau_y = STM_RAW[-2]["y"] * SCREEN_SIZE
        if abs(jean_drapeau_x - x) < 20 and abs(jean_drapeau_y - y) < 34:  # approximation de l'île Sainte-Hélène
            return "Jean-Drapeau"
        else:
            return "Longueuil"
    else:  # île de Montréal
        for dictio in STM_RAW:
            if dictio not in STM_RAW[54:57] or dictio not in STM_RAW[-2:]:  # itère sur toutes les stations de MTL
                candidat = (dictio["x"] * SCREEN_SIZE, dictio["y"] * SCREEN_SIZE)
                if math.dist(coord, candidat) < dist_min:  # si la distance est plus petite que précédemment
                    dist_min = math.dist(coord, candidat)
                    station = dictio["name"]

    return station


def get_coord_from_sommet(sommet: str):
    """Prend en argument le nom d'une station et retourne ses coordonnées"""
    for dictio in STM_RAW:
        if sommet.lower() == dictio["name"].lower():
            return dictio["x"], dictio["y"]


def get_sommet_name(sommet: str):
    """Get the true sommet name"""
    for dictio in STM_RAW:
        if sommet.lower() == dictio["name"].lower():
            return dictio["name"]


def find_the_line(station: str):
    """'Prend en argument le nom d'une station et retourne un ensemble de toutes les lignes de cette station"""
    lines = set()
    for dictio in orange_raw:
        if dictio["name"].lower() == station.lower():
            lines.add("orange")
    for dictio in green_raw:
        if dictio["name"].lower() == station.lower():
            lines.add("verte")
    for dictio in blue_raw:
        if dictio["name"].lower() == station.lower():
            lines.add("bleue")
    for dictio in yellow_raw:
        if dictio["name"].lower() == station.lower():
            lines.add("jaune")
    return lines


def walk_is_doable(destination: str, coord_start: list):
    """Prend le nom de la station finale et les coordonnées initiales de l'utilisateur entre -0.5 et 0.5
    et retourne un booléen qui dit si la marche est un moyen de transport réaliste"""
    coord_end = get_coord_from_sommet(destination)
    if math.dist(coord_start, coord_end) < 0.15:
        return True
    return False


def staying_on_one_line(first_station: str, last_station: str):
    """Prend en argument le nom de la première station visitée et de la station finale et retourne la ligne commune ou None s'il n'y en a pas """
    first_station_lines = find_the_line(first_station)
    last_station_lines = find_the_line(last_station)
    common_lines = first_station_lines & last_station_lines  # "ET" logique pour trouver la ligne commune
    if common_lines:
        return list(common_lines)[0]  # retourne un string
    return


###################################
############ MAIN LOOP ############
###################################

ANIMATION_END_DELAY = -1


# ASK ORIGIN
def on_screen_click(*coord):
    """Handler for turtle's screen click's event"""
    global GAME_STATE, ORIGIN, ORIGIN_COORD, ANIMATION_END_DELAY
    if GAME_STATE == ALL_GAME_STATES["INTRO"] and intro_button.state == intro_button.ALL_STATES['pulse']:
        intro_button.state = intro_button.ALL_STATES['grow']
    if GAME_STATE == ALL_GAME_STATES["ASK_ORIGIN"]:
        ORIGIN_COORD = coord
        possible_origin = STM.sommet(closest_station(coord))
        if not possible_origin:
            print("Please try again.")  # todo: replace with on-screen message
            return
        ORIGIN = possible_origin
        GAME_STATE = ALL_GAME_STATES["ASK_DESTINATION"]


def handle_ask_destination():
    """Handle the operations to be done when the game's state is 'ASK_DESTINATION'"""
    global GAME_STATE, DESTINATION, ROUTE, ANIMATION_END_DELAY

    destination_str = turtle.textinput(
        f"De {str(ORIGIN)} à quelle station?",
        "Veuillez entrer le nom d'une station du métro de Montréal",
        # Explications détaillées : https://youtu.be/dQw4w9WgXcQ
    )

    if not destination_str:
        # User has clicked cancel, reset game state to previous one
        GAME_STATE = ALL_GAME_STATES["ASK_ORIGIN"]
        return

    possible_destination = STM.sommet(get_sommet_name(destination_str))
    if not possible_destination:
        print("Please enter an existing metro station name.")  # todo: replace with something else (?)
        return

    # existing destination, prepare grounds for animation
    DESTINATION = possible_destination

    # find the shortest path to destination using dijkstra
    ROUTE = File()
    route = dijkstra(STM, ORIGIN, DESTINATION)

    # determine whether there is an option to stay on one single line to reach destination
    stays_on_one_line: set[str] | None = {"orange", "verte", "bleue", "jaune"}
    for p in route["p"]:
        ROUTE.enfile(p)
        stays_on_one_line &= find_the_line(str(p))

    line_to_stay_on = staying_on_one_line(str(ORIGIN), destination_str)
    if line_to_stay_on and not stays_on_one_line:
        # offer the option to stay on one line
        one_line = turtle.textinput(
            "Une ligne",
            "Souhaitez-vous absolument rester sur la même ligne? Répondez «oui» ou cliquez «annuler».",
        )
        if one_line and one_line.lower() == "oui":
            ROUTE = File()
            line = LINES[line_to_stay_on]
            route = dijkstra(
                line,
                line.sommet(closest_station(ORIGIN_COORD)),
                line.sommet(get_sommet_name(destination_str)),
            )
            for p in route["p"]:
                ROUTE.enfile(p)

    # offer the option to walk to destination directly
    adapted_coord = [i / SCREEN_SIZE for i in ORIGIN_COORD]
    if walk_is_doable(destination_str, adapted_coord):
        walk_decision = turtle.textinput(
            "Marche",
            "Préférez-vous marcher jusqu'à votre destination? Répondez «oui» ou cliquez «annuler».",
        )
        if walk_decision and walk_decision.lower() == "oui":
            ROUTE = File()
            ROUTE.enfile(destination_str)

    # Setup everything for the animation part
    GAME_STATE = ALL_GAME_STATES["ANIMATE"]
    # if ROUTE.taille() == 1:
    #     user.set_destination_from_coord(ORIGIN_COORD)
    # else:
    #     user.set_destination(str(ROUTE.defile()))
    user.set_destination_from_coord(ORIGIN_COORD)
    user.showturtle()
    user.teleport_to_destination()
    bg.set_dynamic_map()
    bg.reset_follow_cam_position()
    ANIMATION_END_DELAY = 60


def handle_animate():
    """Handle the operations to be done when the game's state is 'ANIMATE'"""
    global GAME_STATE, ANIMATION_END_DELAY

    # make the background/follow camera to dynamically follow user
    bg.follow_user(map(lambda e: -e * BG_RATIO, user.get_coord()))
    # animate the user
    has_arrived_at_subdestination = user.loop(ROUTE.taille())
    if has_arrived_at_subdestination:
        # subdestination has arrived, pick the next subdestination
        if ROUTE.estvide():
            # No more subdestination in queue, wait 60 frames before animating confettis
            if ANIMATION_END_DELAY == 0:
                GAME_STATE = ALL_GAME_STATES["END"]
                user.reset_after_animation()
                bg.set_normal_map()
                confetti.reset()
                ANIMATION_END_DELAY = 150
            else:
                ANIMATION_END_DELAY -= 1
        else:
            # Set new subdestination
            user.set_destination(str(ROUTE.defile()))


def handle_end():
    """Handle the operations to be done when the game's state is 'END'"""
    global GAME_STATE, DESTINATION, ROUTE, ANIMATION_END_DELAY, confetti

    if ANIMATION_END_DELAY == 0:
        # Les confettis sont animés ; reset le programme pour une autre animation de la STM!!
        GAME_STATE = ALL_GAME_STATES["ASK_ORIGIN"]
    else:
        # Animer les confettis
        confetti.animate()
        ANIMATION_END_DELAY -= 1


def handle_intro():
    """Handle every operation related to the intro screen"""
    global GAME_STATE

    if intro_button.state == intro_button.ALL_STATES['pulse']:
        intro_button.pulse()
    if intro_button.state == intro_button.ALL_STATES['grow']:
        display_map = intro_button.grow()
        if display_map:
            bg.set_normal_map()
    if intro_button.state == intro_button.ALL_STATES['shrink']:
        change_next_game_state = intro_button.shrink()
        if change_next_game_state:
            intro_button.hideturtle()
            intro_button.state = intro_button.ALL_STATES['inactive']
            GAME_STATE = ALL_GAME_STATES["ASK_ORIGIN"]


def update():
    """THE GAME'S MAIN LOOP, CALLED EVERY 16MS (standard 60fps)"""
    if GAME_STATE == ALL_GAME_STATES["INTRO"]:
        label.print("Bienvenue dans notre simulation de la STM!", (0, SCREEN_SIZE / 3.5))
        label.print('Par Jeanne Cazelais et Junyi Zhang', 0, -SCREEN_SIZE / 2.5, erase=False)
        handle_intro()

    if GAME_STATE == ALL_GAME_STATES["ASK_ORIGIN"] or intro_button.state == intro_button.ALL_STATES['shrink']:
        # the ASK_ORIGIN game state is handled separately with turtle's on_screen_click listener
        label.print("Veuillez sélectionner votre point de départ :D", 0, SCREEN_SIZE / 2 - 80)

    if GAME_STATE == ALL_GAME_STATES["ASK_DESTINATION"]:
        handle_ask_destination()
        label.clear()
    if GAME_STATE == ALL_GAME_STATES["ANIMATE"]:
        handle_animate()
    if GAME_STATE == ALL_GAME_STATES["END"]:
        label.print("Vous êtes arrivé(e) à votre destination!!!", 0, SCREEN_SIZE / 2 - 80)
        handle_end()

    screen.update()
    screen.ontimer(update, 16)


turtle.onscreenclick(on_screen_click)

update()
screen.mainloop()
