import numpy as np

timestep = 0.1
verbose = False

printif = print if verbose else lambda *a, **k: None


class agent:
    def __init__(self, id, position, speed, velocity_unit_vector, theta, turning_angle):
        self.id = id
        xdata = 10 * np.arange(0, 1, 0.1)
        self.pos = (
            xdata,
            np.sin(xdata) + 0.1 * np.random.randn(1),
            np.cos(xdata) + 0.1 * np.random.randn(1),
        ) if position is None else position
        vxdata = 0.1
        vydata = np.sin(vxdata) + 0.1 * np.random.randn(1)
        vzdata = np.cos(vxdata) + 0.1 * np.random.randn(1)
        self.velocity_unit_vector = tuple((vxdata, vydata[0], vzdata[0]))
        varray = np.array(self.velocity_unit_vector)
        varray = unit_vector(varray)
        self.velocity_unit_vector = tuple(varray)

        self.speed = 1 if speed is None else speed
        self.vision = 360 if theta is None else theta
        self.turning_angle = 40 if turning_angle is None else turning_angle


def unit_vector(vector):
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    """Calculate angle between two vectors."""
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def euclidean_distance(r1, r2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(r2 - r1)

