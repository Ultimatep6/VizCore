class Rect:
    """
    Defines rectangle geometry used by layout system.

    Responsibilities:
        - Store position and dimensions
        - Provide helper geometry operations
    """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, px, py):
        """Check if a point (px, py) is inside the rectangle."""
        return (self.x <= px < self.x + self.width) and (self.y <= py < self.y + self.height)

    def intersect(self, other):
        """Return intersection rectangle or None if no overlap."""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        if x1 < x2 and y1 < y2:
            return Rect(x1, y1, x2 - x1, y2 - y1)
        return None

    def area(self):
        """Return area of the rectangle."""
        return self.width * self.height

    def as_tuple(self):
        """Return (x, y, width, height) as a tuple."""
        return (self.x, self.y, self.width, self.height)