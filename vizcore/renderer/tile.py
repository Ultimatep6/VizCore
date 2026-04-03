class Tile:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.widget = None

    def __repr__(self):
        return f"Tile(x={self.x}, y={self.y}, w={self.width}, h={self.height}, widget={self.widget is not None})"

class TileManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [Tile(0, 0, width, height)]
        self.focus_index = 0  # Start with the whole window focused

    def split_focused_tile(self, direction='vertical'):
        tile = self.tiles[self.focus_index]
        if direction == 'vertical':
            w = tile.width // 2
            t1 = Tile(tile.x, tile.y, w, tile.height)
            t2 = Tile(tile.x + w, tile.y, tile.width - w, tile.height)
        else:  # horizontal
            h = tile.height // 2
            t1 = Tile(tile.x, tile.y, tile.width, h)
            t2 = Tile(tile.x, tile.y + h, tile.width, tile.height - h)
            
        t1.widget = tile.widget # Carry over existing widget to the primary split tile
        
        # Replace focused tile with the two new tiles
        self.tiles.pop(self.focus_index)
        self.tiles.insert(self.focus_index, t2)
        self.tiles.insert(self.focus_index, t1)

    def set_focus(self, index):
        if 0 <= index < len(self.tiles):
            self.focus_index = index

    def __repr__(self):
        return f"Tiles: {self.tiles}\nFocused: {self.focus_index}"



