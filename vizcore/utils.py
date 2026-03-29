import numpy as np

def rotation_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]], dtype="f4")

def rotation_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]], dtype="f4")

def translation(tx, ty, tz):
    return np.array([[1,0,0,tx],[0,1,0,ty],[0,0,1,tz],[0,0,0,1]], dtype="f4")

def perspective(fov, aspect, near, far):
    f = 1 / np.tan(fov / 2)
    return np.array([
        [f/aspect, 0,                    0,                       0],
        [0,        f,                    0,                       0],
        [0,        0, (far+near)/(near-far), (2*far*near)/(near-far)],
        [0,        0,                   -1,                       0]
    ], dtype="f4")


def combine_meshes(verts_a, inds_a, verts_b, inds_b):
    offset = len(verts_a)
    combined_verts = np.concatenate([verts_a, verts_b], axis=0)
    combined_inds  = np.concatenate([inds_a, inds_b + offset], axis=0)
    return combined_verts, combined_inds