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

    def get_border_at(self, x, y, threshold=5):
        for tile in self.tiles:
            if abs(x - tile.x) < threshold and tile.x != 0:
                if tile.y <= y <= tile.y + tile.height:
                    return ('vertical', tile.x)
            if abs(x - (tile.x + tile.width)) < threshold and tile.x + tile.width != self.width:
                if tile.y <= y <= tile.y + tile.height:
                    return ('vertical', tile.x + tile.width)
                    
            if abs(y - tile.y) < threshold and tile.y != 0:
                if tile.x <= x <= tile.x + tile.width:
                    return ('horizontal', tile.y)
            if abs(y - (tile.y + tile.height)) < threshold and tile.y + tile.height != self.height:
                if tile.x <= x <= tile.x + tile.width:
                    return ('horizontal', tile.y + tile.height)
        return None

    def resize_border(self, x, y, dx, dy, threshold=5):
        border = self.get_border_at(x, y, threshold)
        if not border:
            return 0, 0
            
        btype, val = border
        min_size = 20
        
        if btype == 'vertical':
            left_tiles = [t for t in self.tiles if t.x + t.width == val]
            right_tiles = [t for t in self.tiles if t.x == val]
            if not left_tiles or not right_tiles: return 0, 0
            
            max_neg = min([t.width - min_size for t in left_tiles] + [float('inf')])
            max_pos = min([t.width - min_size for t in right_tiles] + [float('inf')])
            clamped_dx = max(-max_neg, min(max_pos, dx))
            
            for t in left_tiles:
                t.width += clamped_dx
            for t in right_tiles:
                t.x += clamped_dx
                t.width -= clamped_dx
            return clamped_dx, 0
        else:
            bottom_tiles = [t for t in self.tiles if t.y + t.height == val]
            top_tiles = [t for t in self.tiles if t.y == val]
            if not bottom_tiles or not top_tiles: return 0, 0
            
            max_neg = min([t.height - min_size for t in bottom_tiles] + [float('inf')])
            max_pos = min([t.height - min_size for t in top_tiles] + [float('inf')])
            clamped_dy = max(-max_neg, min(max_pos, dy))
            
            for t in bottom_tiles:
                t.height += clamped_dy
            for t in top_tiles:
                t.y += clamped_dy
                t.height -= clamped_dy
            return 0, clamped_dy

    def can_merge(self, i, j):
        t1, t2 = self.tiles[i], self.tiles[j]
        if t1.height == t2.height and t1.y == t2.y:
            if t1.x + t1.width == t2.x or t2.x + t2.width == t1.x:
                return True
        if t1.width == t2.width and t1.x == t2.x:
            if t1.y + t1.height == t2.y or t2.y + t2.height == t1.y:
                return True
        return False

    def merge(self, i, j):
        if not self.can_merge(i, j): 
            return False
            
        t1, t2 = self.tiles[i], self.tiles[j]
        min_x = min(t1.x, t2.x)
        min_y = min(t1.y, t2.y)
        max_x = max(t1.x + t1.width, t2.x + t2.width)
        max_y = max(t1.y + t1.height, t2.y + t2.height)
        
        t1.x, t1.y = min_x, min_y
        t1.width, t1.height = max_x - min_x, max_y - min_y
        if not t1.widget:
            t1.widget = t2.widget
            
        del self.tiles[j]
        self.focus_index = min(self.focus_index, len(self.tiles) - 1)
        return True

    def __repr__(self):
        return f"Tiles: {self.tiles}\nFocused: {self.focus_index}"



