import numpy as np
from keynet.blockpermute import block_permute, hierarchical_block_permute, hierarchical_block_permutation_matrix
import vipy.image


def show_corner_block_permutation():
    img = np.zeros( (256,256,3) ).astype(np.uint8)
    img[0:16,0:16,:] = [255,0,0]
    img[0:16,-16:] = [0,255,0]
    img[-16:,0:16] = [0,0,255]
    img[-16:,-16:] = [255,255,255]

    img_permuted = block_permute(img, (64,64) )
    vipy.image.Image(array=img).close().show()
    vipy.image.Image(array=img_permuted).show()
    
    
def show_image_block_permutation(imgfile='owl.jpg'):
    im = vipy.image.Image(imgfile).resize(512, 512, interp='nearest')
    img_permuted = block_permute(im.array(), (128,128))
    im.close().show()
    vipy.image.Image(array=img_permuted).show()

    
def show_local_hierarchical_block_permutation(imgfile='owl.jpg'):
    im = vipy.image.Image(imgfile).resize(512, 512, interp='nearest')
    img_permuted = hierarchical_block_permute(im.array(), num_blocks=(2,2), permute_at_level=[4,5])
    im.close().show()
    vipy.image.Image(array=img_permuted).show()

    
def show_global_hierarchical_block_permutation_2x2(imgfile='owl.jpg'):
    im = vipy.image.Image(imgfile).resize(512, 512, interp='nearest')
    img_permuted = hierarchical_block_permute(im.array(), num_blocks=(2,2), permute_at_level=[0,1,2,3,4,5])
    im.close().show()
    vipy.image.Image(array=img_permuted).show()
    
    
def show_global_hierarchical_block_permutation_3x3(imgfile='owl.jpg'):
    im = vipy.image.Image(imgfile).resize(486, 486, interp='nearest')
    img_permuted = hierarchical_block_permute(im.array(), num_blocks=(3,3), permute_at_level=[0,1,2,3])
    im.close().show()
    vipy.image.Image(array=img_permuted).show()


def show_global_hierarchical_block_permutation_grey_2x3(imgfile='owl.jpg'):
    im = vipy.image.Image(imgfile).resize(rows=512, cols=486, interp='nearest').greyscale()
    img_permuted = hierarchical_block_permute(im.array(), num_blocks=(2,3), permute_at_level=[0,1,2,3])
    im.close().show()
    vipy.image.Image(array=img_permuted, colorspace='float').show()
    

def test_hierarchical_block_permutation():
    im = vipy.image.Image('owl.jpg').resize(512, 512, interp='nearest')
    img_permuted = hierarchical_block_permute(im.array(), num_blocks=(2,2), permute_at_level=[4,5], seed=42)
    P = hierarchical_block_permutation_matrix(im.array().shape, num_blocks=(2,2), permute_at_level=[4,5], seed=42)

    import pdb; pdb.set_trace()
    assert np.allclose(P.dot(im.array().flatten()), img_permuted.flatten(), atol=1E-5)
    print('[test_blockpermute]: hierarchical_block_permutation  PASSED')
    
