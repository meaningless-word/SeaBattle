import random
from random import randint


class BoardException(Exception):
    pass


class BoardVeryWideException(BoardException):
    def __str__(self):
        return "Не пытайся создать доску за пределами разумного. 28*28 вполне разумный максимум."


class BoardWrongShipException(BoardException):
    pass


class BoardOutException(BoardException):
    def __str__(self):
        return "За пределами доски не играем"


class BoardFiredCellException(BoardException):
    def __str__(self):
        return "Эта клетка уже обстреливалась"


class Cell:
    def __init__(self, row, col, frame=0):
        self.row = row
        self.col = col
        self.frame = frame

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __repr__(self):
        return f"({self.row}:{self.col})/{self.frame}"

    @property
    def unpacker(self):
        return (self.row, self.col, self.frame)


class Ship:
    def __init__(self, bow, decks, orient):
        """
        Корабль
        :param bow: клетка расположения носа корабля
        :param decks: количество палуб
        :param orient: направление на доске (v/h - вертикально/горизонтально
        """
        self.__bow = bow
        self.__decks = decks
        self.__orient = orient
        self.resist = decks

    @property
    def cells(self):
        dimensions = []
        for i in range(self.__decks):
            r, c, f = self.__bow.unpacker
            if self.__orient == "h":
                c += i
                f = 5 | (8 if i == 0 else 0) | (2 if i == self.__decks - 1 else 0)
            if self.__orient == "v":
                r += i
                f = 10 | (1 if i == 0 else 0) | (4 if i == self.__decks - 1 else 0)
            dimensions.append(Cell(r, c, f))
        return dimensions

    def is_shooten(self, shot):
        return shot in self.cells

# немного лирики:
# чтобы сделать неограниченную размерность доски, необходимо дополнить буквенный ряд
# нужно помнить, что на отображение индексов колонок и строк отведено всего 3 знакоместа, дальше доска может расползтись
# к тому же, где взять столько букв? буквенный индекс состоит из одного символа
# изначально параметр размера зафиксируем на классической отметке 10
# а пока размер доски ограничен буквенным рядом из 28 символов
class Bay:
    def __init__(self, event, size=10):
        self.letters = list("абвгдежзиклмропрстуфхцшщыэюя")
        if size > len(self.letters):
            raise BoardVeryWideException()
        self.size = size
        self.__event = event
        self.cells = [[""] * size for _ in range(size)]
        self.ships = []
        self.busy = []
        self.sunken_ships = 0

    def draw_bay(self, can_see: bool = False):
        result = [" "*4 + " ".join([f"{i:^3}" for i in self.letters[:self.size]])]

        frames = []
        for i in range(self.size):
            frames.append(["   ", "+"] * (self.size + 1))
            frames.append([f"{i + 1:^3}", " ", *[item for pair in zip([f"{cell:^3}" for cell in self.cells[i]], [" "] * self.size) for item in pair]])
        frames.append(["   ", "+"] * (self.size + 1))

        for s in self.ships:
            h_line = " ~ " if s.resist == 0 else "---" if can_see else "   "
            v_line = ":" if s.resist == 0 else "|" if can_see else " "
            for d in s.cells:
                if d.frame & 1 == 1:
                    frames[d.row * 2][d.col * 2 + 2] = h_line
                if d.frame & 2 == 2:
                    frames[d.row * 2 + 1][d.col * 2 + 3] = v_line
                if d.frame & 8 == 8:
                    frames[d.row * 2 + 1][d.col * 2 + 1] = v_line
                if d.frame & 4 == 4:
                    frames[d.row * 2 + 2][d.col * 2 + 2] = h_line

        for f in frames:
            result.append("".join(f))

        return result

    def __str__(self):
        return "\n".join(self.draw_bay())

    def put_ship(self, ship):
        # проверка - все ли клетки корабля помещаются на доске
        for c in ship.cells:
            if self.out(c) or c in self.busy:
                raise BoardWrongShipException()
        # если на проверке не словили исключение, добавляем в бухту
        for c in ship.cells:
            self.busy.append(c)
        # добавляем корабль в список кораблей
        self.ships.append(ship)
        # в занятые клетки добавляем "водоизмещение" - мертвую зону вокруг корабля, куда запрещено помещать другие
        self.displacement(ship)

    def displacement(self, ship, mark_with=""):
        for c in ship.cells:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    cell = Cell(c.row + dr, c.col + dc)
                    if not (self.out(cell) or cell in self.busy):
                        self.busy.append(cell)
                        if mark_with:
                            self.cells[cell.row][cell.col] = mark_with

    def out(self, d):
        """
        Проверка координат на выход за границы доски
        :param d:
        :return:
        """
        return not ((0 <= d.row < self.size) and (0 <= d.col < self.size))

    @property
    def capacity(self):
        """
        Вместимость бухты - сколько кораблей можно разместить согласно плотности кораблей в игре 10*10
        :return: list[int]
        """
        result = []
        # в классической игре 10*10 кораблей: 1 четырёхпалубник, 2 трёхпалубника, 3 двухпалубника и 4 однопалубника
        # итого 4 + 2*3 + 3*2 + 4 = 20 палуб на доске в 100 клеток, т.е. 20% поля занимают корабли
        decks = int(self.size * self.size * 0.2)
        i = 1
        while decks > 0:
            for j in range(1, i + 1):
                result.append(j if decks > j else decks)
                decks -= j
                if decks < 0:
                    break
            i += 1
        result.sort(reverse=True)
        return result

    def shot(self, cell):
        if self.out(cell):
            raise BoardOutException()

        if cell in self.busy:
            raise BoardFiredCellException()

        self.busy.append(cell)
        for ship in self.ships:
            if cell in ship.cells:
                ship.resist -= 1
                self.cells[cell.row][cell.col] = "БДЩ"
                if ship.resist == 0:
                    self.sunken_ships += 1
                    self.displacement(ship, "·")
                    self.__event.message = "Убит :.("
                else:
                    self.__event.message = "Ранен :("
                return True

        self.cells[cell.row][cell.col] = "•"
        self.__event.message = "Мимо!"
        return False

    def begin(self):
        self.busy = []


class Player:
    def __init__(self, my_bay, enemy_bay):
        self.my_bay = my_bay
        self.enemy_bay = enemy_bay

    def ask(self):
        raise NotImplementedError()

    def move(self):
        while True:
            try:
                target = self.ask()
                shot = self.enemy_bay.shot(target)
                return shot
            except BoardException as e:
                print(e)


class Human(Player):
    def ask(self):
        while True:
            pos = input("твой ход ->")
            # отделяем число от координатной строки, которое должно заканчивать выражение
            i = -1
            while pos[i:].isdigit() and len(pos) >= -i:
                i -= 1

            if not (pos[i + 1:].isdigit() and pos[0:i + 1].isalpha()):
                print("чёт не похоже на координаты, ну-ка снова...")
                continue
            if self.my_bay.letters.count(pos[0:i + 1]) == 0:
                print("нет такой буквы в этой системе координат, повтори...")
                continue

            row = int(pos[i + 1:]) - 1
            col = self.my_bay.letters.index(pos[0:i + 1])
            return Cell(row, col)

    def show_board(self):
        lines = list(zip(self.my_bay.draw_bay(True), self.enemy_bay.draw_bay()))
        print("\n".join([x + " " * 10 + y for x, y in lines]))


class Cyber(Player):
    def ask(self):
        cell = Cell(randint(0, self.my_bay.size - 1), randint(0, self.my_bay.size - 1))
        print(f"мой ход ->{self.my_bay.letters[cell.col]}{cell.row + 1}")
        return cell


# хотелось перенести сообщение о результате прошлого хода после отрисовки доски, которое выполняется в начале каждого игрового цикла
class LastEvent:
    def __init__(self):
        self.message = ""
        self.hurt_ship = []

    def __str__(self):
        return self.message


class Game:
    def __init__(self, size=10):
        self.__event = LastEvent()
        self.__size = size
        self.human_bay = self.get_random_bay()
        self.cyber_bay = self.get_random_bay()

        self.cyber = Cyber(self.cyber_bay, self.human_bay)
        self.human = Human(self.human_bay, self.cyber_bay)

    def get_random_bay(self):
        bay = None
        while bay is None:
            bay = self.place_randomly()
        return bay

    def place_randomly(self):
        bay = Bay(self.__event, self.__size)
        attempts = 0
        for ship_model in bay.capacity:
            while True:
                attempts += 1
                if attempts > 2000:
                    return None
                ship = Ship(Cell(randint(0, self.__size), randint(0, self.__size)), ship_model, random.choice(["h", "v"]))
                try:
                    bay.put_ship(ship)
                    break
                except BoardException:
                    pass
        bay.begin()
        return bay

    def welcome(self):
        print("""
        +--+--+--+     
+--+  +--+ +--+--+     
|   \/   | О Р С К О Й 
+  +  +  + +--+--.     
|  |\/|  | +--.  |     
+--+  +--+ |  |  | О Й    
        |  +--'  |     
        +--+--+--'                     
        """)

    def process(self):
        turn = 0
        while True:
            self.human.show_board()
            print(self.__event)
            if turn % 2 == 0:
                repeat = self.human.move()
            else:
                repeat = self.cyber.move()
            turn -= repeat

            if self.cyber.my_bay.sunken_ships == len(self.cyber.my_bay.capacity):
                self.__event.message = "Твоя победа"
                break

            if self.human.my_bay.sunken_ships == len(self.human.my_bay.capacity):
                self.__event.message = "Я выиграл!"
                break

            turn += 1

        self.human.show_board()
        print(self.__event)

    def start(self):
        self.welcome()
        self.process()


g = Game()
g.start()

