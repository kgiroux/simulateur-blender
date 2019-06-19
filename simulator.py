from distutils.util import strtobool

import bpy
import datetime
import bmesh
import math
from math import radians
import random
import os
import json
from collections import Counter

VIRTUAL_OBJECT = "VIRTUAL_OBJECT"
CONFIGURATION_OBJECT = "CONFIGURATION_OBJECT"
g_nb_objects = None
g_texture_files = None
g_texture_files_box = None
g_debugMode = None
g_folder_scenario = "NOT_DEFINED"


def add_texture_to_object(p_object_name,
                          p_index_object,
                          p_iteration_object,
                          p_texture_path,
                          p_material_type="ShaderNodeBsdfDiffuse"):
    if os.path.exists(os.path.realpath(p_texture_path)):
        # ---------------------------------------------------------------
        # adding the chosen texture
        # ---------------------------------------------------------------
        # Get material
        obj = bpy.data.objects.get(p_object_name)
        material_name = p_object_name + "_" + str(p_index_object) + "_" + str(p_iteration_object) + "_material"
        mat = bpy.data.materials.get(material_name)
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name=material_name)

        # Assign it to object
        if obj.data.materials:
            # assign to 1st material slot
            obj.data.materials[0] = mat
        else:
            # no slots
            obj.data.materials.append(mat)

        mat.use_nodes = True
        nt = mat.node_tree
        nodes = nt.nodes
        links = nt.links

        # clear
        while nodes:
            nodes.remove(nodes[0])

        output = nodes.new("ShaderNodeOutputMaterial")
        material_node = nodes.new(p_material_type)
        links.new(output.inputs['Surface'], material_node.outputs['BSDF'])

        # chargement et application de l'image de texture
        texture = nodes.new("ShaderNodeTexImage")
        uvmap = nodes.new("ShaderNodeUVMap")
        im = bpy.data.images.get(os.path.basename(os.path.realpath(p_texture_path)))
        if im is None:
            im = bpy.data.images.load(os.path.realpath(p_texture_path))
        texture.image = im
        uvmap.uv_map = "UVMap"
        links.new(material_node.inputs['Color'], texture.outputs['Color'])
        links.new(texture.inputs['Vector'], uvmap.outputs['UV'])


def add_deformations(p_duplicated_object,
                     p_scene,
                     p_scale_min,
                     p_scale_max,
                     p_options):
    # active l'instance en cours
    p_scene.objects.active = p_duplicated_object

    # applique des déformations
    if p_options[0]:  # random.uniform(0, 100) > 60:
        displace = p_duplicated_object.modifiers.new(name='displace', type='DISPLACE')
        displace.strength = 0.008
        displace.mid_level = 0.005
        displace.direction = 'RGB_TO_XYZ'

        displace.strength = 0.006
        displace.direction = 'RGB_TO_XYZ'
        displace_texture = bpy.data.textures.new('displace_texture', type='STUCCI')
        displace_texture.noise_type = 'HARD_NOISE'
        displace_texture.stucci_type = 'WALL_OUT'
        displace_texture.noise_scale = 0.08
        displace_texture.turbulence = 180
        displace_texture.noise_basis = 'IMPROVED_PERLIN'

        displace_texture = bpy.data.textures.new('displace_texture', type='CLOUDS')
        displace_texture.noise_type = 'HARD_NOISE'
        displace_texture.cloud_type = 'COLOR'
        displace_texture.noise_scale = random.uniform(0.04, 0.08)  # stick
        displace_texture.noise_depth = random.uniform(1, 3)
        displace_texture.noise_basis = 'VORONOI_F2'

        displace.texture = displace_texture

    if p_options[1]:
        cast_cylinder = p_duplicated_object.modifiers.new(name='cast_cylinder', type='CAST')
        cast_cylinder.cast_type = 'CYLINDER'
        cast_cylinder.use_x = True
        cast_cylinder.use_y = True
        cast_cylinder.use_z = True
        cast_cylinder.radius = 0.05
        cast_cylinder.use_radius_as_size = True
        cast_cylinder.factor = random.uniform(-0.05, 0.25)

    if p_options[2]:
        cast_sphere = p_duplicated_object.modifiers.new(name='cast_sphere', type='CAST')
        cast_sphere.cast_type = 'SPHERE'
        cast_sphere.use_x = False
        cast_sphere.use_y = True
        cast_sphere.use_z = False
        cast_sphere.radius = 0.05
        cast_sphere.use_radius_as_size = True
        cast_sphere.factor = random.uniform(-0.1, 0.1)

    if p_options[3]:
        bevel = p_duplicated_object.modifiers.new('Bevel', 'BEVEL')
        bevel.segments = 10
        bevel.width = 2.5 / 10

    if p_options[4]:
        twist = p_duplicated_object.modifiers.new(name='twist', type='SIMPLE_DEFORM')
        twist.deform_method = 'TWIST'
        twist.angle = random.uniform(7, 10) * math.pi / 180

    if p_options[5]:
        bend = p_duplicated_object.modifiers.new(name='bend', type='SIMPLE_DEFORM')
        bend.deform_method = 'BEND'
        bend.angle = random.uniform(0, 30) * math.pi / 180

    if p_options[6]:
        taper = p_duplicated_object.modifiers.new(name='taper', type='SIMPLE_DEFORM')
        taper.deform_method = 'TAPER'
        taper.factor = random.uniform(0.1, 0.8)

    bpy.ops.object.visual_transform_apply()

    # modifie l'échelle de manière isotropique
    if p_options[7]:
        p_duplicated_object.scale *= random.uniform(p_scale_min, p_scale_max)
        bpy.ops.object.transform_apply(scale=True)

    # modifie l'échelle de manière anisotropique
    if p_options[8]:
        p_duplicated_object.scale[0] *= random.uniform(p_scale_min, p_scale_max)
        p_duplicated_object.scale[1] *= random.uniform(p_scale_min, p_scale_max)
        p_duplicated_object.scale[2] *= random.uniform(p_scale_min, p_scale_max)
        bpy.ops.object.transform_apply(scale=True)


def render_camera(p_context,
                  p_camera,
                  p_folder_name,
                  p_output_name,
                  p_render_rgb=True,
                  p_render_depth=True,
                  p_render_ground_truth=True,
                  p_use_gpu=False):
    a_scene = p_context.scene

    # Save initial render filepath to restore it at the end
    initial_render_filepath = a_scene.render.filepath
    render_layer = a_scene.render.layers['RenderLayer']

    if not p_render_rgb:
        render_layer.use_pass_combined = False

        # Add composing nodes to render additional passes (depth and object_indexes)
    if p_render_depth:
        render_layer.use_pass_z = True

        # Set composing nodes to render the different interesting passes
        a_scene.use_nodes = True
        nodes_tree = a_scene.node_tree
        nodes_links = nodes_tree.links

        # Retrieve default RenderLayers node ( it should exists by default)
        render_layers_node = nodes_tree.nodes['Render Layers']
        
        z_map_node = nodes_tree.nodes.new('CompositorNodeNormalize')
        nodes_links.new(render_layers_node.outputs['Depth'], z_map_node.inputs["Value"] )

        # create depth output node
        depth_output_node = nodes_tree.nodes.new('CompositorNodeOutputFile')
        depth_output_node.location = 0, 0
        depth_output_node.base_path = p_folder_name
        depth_output_node.file_slots[0].path = p_output_name + "_distance_map"
        depth_output_node.format.file_format = 'PNG'
        depth_output_node.format.color_depth = '16'
        depth_output_node.format.color_mode = 'BW'
        nodes_links.new(z_map_node.outputs['Value'], depth_output_node.inputs[0])
        # Composite node for regular rendering should already exist
        
    if p_render_ground_truth:
        render_layer.use_pass_object_index = True

        # Set composing nodes to render the different interesting passes
        a_scene.use_nodes = True
        nodes_tree = a_scene.node_tree
        nodes_links = nodes_tree.links

        # Retrieve default RenderLayers node ( it should exists by default)
        render_layers_node = nodes_tree.nodes['Render Layers']

        # Count the number of dropped objects : those are the ones with object indices
        
        nb_objects = g_nb_objects
        # Create a node to map objects indices to 16bit value
        objectindex_mathnode = nodes_tree.nodes.new('CompositorNodeMath')
        objectindex_mathnode.operation = 'DIVIDE'
        print("NbObject : {}".format(g_nb_objects))
        objectindex_mathnode.inputs[1].default_value = nb_objects
        objectindex_mathnode.location = 200, -300
        # objectindex_mathnode.size = [math.floor((2**16)/(nb_objects))/float(2**16)]
        # Clamp values
        nodes_links.new(render_layers_node.outputs["IndexOB"], objectindex_mathnode.inputs["Value"])

        object_index_output_node = nodes_tree.nodes.new('CompositorNodeOutputFile')
        object_index_output_node.location = 600, -300
        object_index_output_node.base_path = p_folder_name
        object_index_output_node.file_slots[0].path = p_output_name + "_object_index"
        object_index_output_node.format.file_format = 'PNG'
        object_index_output_node.format.color_depth = '16'
        object_index_output_node.format.color_mode = 'BW'
        nodes_links.new(objectindex_mathnode.outputs["Value"], object_index_output_node.inputs['Image'])
    # Render
    a_scene.camera = p_camera
    a_scene.render.image_settings.file_format = 'PNG'
    a_scene.render.filepath = p_folder_name + '/' + p_output_name + "_image"
    if p_use_gpu:
        a_scene.render.tile_x = 256
        a_scene.render.tile_y = 256
        a_scene.cycles.device = 'GPU'
    else:
        a_scene.render.tile_x = 64
        a_scene.render.tile_y = 64
        a_scene.cycles.device = 'CPU'
    bpy.ops.render.render(animation=False, write_still=True, scene=a_scene.name)

    # Rename renders to their definitive name (Blender automatically appends the frame number in case of an animation)
    def rename_blender_output(n):
        wrong_names = [f for f in os.listdir(p_folder_name) if f.startswith(n)]
        if len(wrong_names) == 1:
            os.rename(p_folder_name + '/' + wrong_names[0], p_folder_name + '/' + n + '.png')

    rename_blender_output(p_output_name + '_image')
    rename_blender_output(p_output_name + '_distance_map')
    rename_blender_output(p_output_name + '_object_index')

    # Restore render filepath
    a_scene.render.filepath = initial_render_filepath

    if not p_render_rgb:
        render_layer.use_pass_combined = True
    # Remove added nodes and links
    if p_render_depth:
        nodes_tree.nodes.remove(z_map_node)
        nodes_tree.nodes.remove(depth_output_node)
    if p_render_ground_truth:
        nodes_tree.nodes.remove(objectindex_mathnode)
        nodes_tree.nodes.remove(object_index_output_node)


def generate_folder_scenario(p_iteration):
    """
        Generate a folder_name
    :param p_iteration: iteration for the generation of the folder name
    :return:
    """
    return "output_" + str(p_iteration) + "_" + datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")


def generate_configuration(p_configuration: int,
                           p_layer: int,
                           p_config,
                           p_objects_params):
    """
    Generate a configuration (placement of object) for the current configuration choose
    :param p_configuration: configuration choose
    :param p_layer: layer_level
    :param p_config:  configuration
    :param p_objects_params : array that contains object configuration
    :return:
    """
    width = p_config["width"]
    height = p_config["height"]
    weight = p_config["weight"]
    layer_name = p_config["pattern_layer"]
    separator = p_config["separator"]
    max_use_texture = p_config["max_texture_use"] - 1
    if p_configuration == 0:
        # The configuration 0 is composed by 4 vertical box, and 2 horizontal
        for index_in_range in range(4):
            # Cube 1
            cube_x = -  width
            cube_y = - 3 * width + index_in_range * (2 * width + separator)
            # cube_y = index_in_range * (2 * width + separator)
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append((layer_name % (p_layer, index_in_range),
                                     cube_x,
                                     cube_y,
                                     cube_z,
                                     False,
                                     p_configuration,
                                     random.randint(0, max_use_texture)))

        nb_object_created = 4
        for index_in_range in range(2):
            cube_x = height + separator
            cube_y = - 3 * width + index_in_range * (2 * height + separator) + width + separator
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append((layer_name % (p_layer, index_in_range + nb_object_created),
                                     cube_x,
                                     cube_y,
                                     cube_z,
                                     True,
                                     p_configuration,
                                     random.randint(0, max_use_texture)))
    elif p_configuration == 1:
        for index_in_range in range(2):
            cube_x = - 2 * width
            cube_y = - 1 * height + index_in_range * (2 * height + separator) + separator
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append((layer_name % (p_layer, index_in_range),
                                     cube_x,
                                     cube_y,
                                     cube_z,
                                     True,
                                     p_configuration,
                                     random.randint(0, max_use_texture)))
        nb_object_created = 2
        for index_in_range in range(4):
            cube_x = (3 * width + separator) - 2 * width
            cube_y = - 1.5 * height + index_in_range * (2 * width + separator)
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append((layer_name % (p_layer, index_in_range + nb_object_created),
                                     cube_x,
                                     cube_y,
                                     cube_z,
                                     False,
                                     p_configuration,
                                     random.randint(0, max_use_texture)))
    elif p_configuration == 2:
        nb_object_created = 0
        cube_x = -2 * width
        cube_y = width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append((layer_name % (p_layer, nb_object_created),
                                 cube_x,
                                 cube_y,
                                 cube_z,
                                 True,
                                 p_configuration,
                                 random.randint(0, max_use_texture)))

        nb_object_created = 1
        for index_in_range in range(2):
            cube_x = (3 * width + separator) - 2 * width
            cube_y = index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append((layer_name % (p_layer, index_in_range + nb_object_created),
                                     cube_x,
                                     cube_y,
                                     cube_z,
                                     False,
                                     p_configuration,
                                     random.randint(0, max_use_texture)))

        nb_object_created = 3
        for index_in_range in range(2):
            cube_x = - 1 * width
            cube_y = (2 * height + 2 * separator) + index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 5

        cube_x = (2 * width + separator) + height - 2 * width
        cube_y = (2 * height + separator) + width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))
    elif p_configuration == 3:
        nb_object_created = 0
        for index_in_range in range(2):
            cube_x = - width
            cube_y = index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))
        nb_object_created = 2

        cube_x = (2 * width + separator) + height - 2 * width
        cube_y = width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 3

        cube_x = -2 * width
        cube_y = (2 * height + separator) + width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))
        nb_object_created = 4
        for index_in_range in range(2):
            cube_x = (3 * width + separator) - 2 * width
            cube_y = (2 * height + 2 * separator) + index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))
    elif p_configuration == 4:
        nb_object_created = 0
        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))
        nb_object_created = 3

        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = (2 * height + separator) + width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))
    elif p_configuration == 5:
        nb_object_created = 0

        cube_x = - width
        cube_y = 0 - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             False,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 1
        for index_in_range in range(2):
            cube_x = index_in_range * (2 * width + 0.5 * separator) - 2 * width
            cube_y = (3 * width) + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 3

        cube_x = width - 2 * width
        cube_y = (2 * width) + (2 * height) + (2 * separator) - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             False,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 4
        for index_in_range in range(2):
            cube_x = (height + 2 * width + separator) - 2 * width
            cube_y = index_in_range * (2 * height + separator) + width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))
    elif p_configuration == 6:
        nb_object_created = 0
        for index_in_range in range(2):
            cube_x = - 2 * width
            cube_y = index_in_range * (2 * height + separator) + width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 2

        cube_x = width
        cube_y = 0 - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             False,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 3
        for index_in_range in range(2):
            cube_x = 2 * width + index_in_range * (2 * width + 0.5 * separator) - 2 * width
            cube_y = (3 * width) + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 5
        cube_x = 3 * width - 2 * width
        cube_y = 2 * width + 2 * height + 2 * separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             False,
             p_configuration,
             random.randint(0, max_use_texture)))
    elif p_configuration == 7:
        nb_object_created = 0
        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 3
        for index_in_range in range(2):
            cube_x = width - 2 * width
            cube_y = (2 * height + 2 * separator) + index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 5
        cube_x = (2 * width + separator) + height - 2 * width
        cube_y = (2 * height + separator) + width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))
    elif p_configuration == 8:
        nb_object_created = 0
        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, nb_object_created + index_in_range),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 3

        cube_x = -  2 * width
        cube_y = (2 * height + separator) + width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 4
        for index_in_range in range(2):
            cube_x = (3 * width + separator) - 2 * width
            cube_y = (2 * height + 2 * separator) + index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))
    elif p_configuration == 9:
        nb_object_created = 0
        cube_x = 0 - 2 * width
        cube_y = width + separator - 1.5 * height
        cube_z = 2 * weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 1
        for index_in_range in range(2):
            cube_x = 3 * width + separator - 2 * width
            cube_y = index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))

        nb_object_created = 3
        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = (2 * height + separator) + width + separator - 1.5 * height
            cube_z = 2 * weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))
    elif p_configuration == 10:
        nb_object_created = 0
        for index_in_range in range(2):
            cube_x = width - 2 * width
            cube_y = index_in_range * (2 * width + separator) - 1.5 * height
            cube_z = 2 + weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 False,
                 p_configuration,
                 random.randint(0, max_use_texture)))
        nb_object_created = 2

        cube_x = 2 * width + separator + height - 2 * width
        cube_y = width + separator - 1.5 * height
        cube_z = 2 + weight + p_layer * (2 * weight + separator)
        p_objects_params.append(
            (layer_name % (p_layer, nb_object_created),
             cube_x,
             cube_y,
             cube_z,
             True,
             p_configuration,
             random.randint(0, max_use_texture)))

        nb_object_created = 3
        for index_in_range in range(3):
            cube_x = index_in_range * (2 * width + separator) - 2 * width
            cube_y = (2 * height + separator) + width + separator - 1.5 * height
            cube_z = 2 + weight + p_layer * (2 * weight + separator)
            p_objects_params.append(
                (layer_name % (p_layer, index_in_range + nb_object_created),
                 cube_x,
                 cube_y,
                 cube_z,
                 True,
                 p_configuration,
                 random.randint(0, max_use_texture)))

    return p_objects_params


def generate_texture_array(p_config):
    """
    Generate a list of texture
    :param p_config: configuration
    :return: array of id texture
    """
    texture_choose = []
    for i in range(p_config["max_texture_use"]):
        texture_choose.append(random.randint(0, len(g_texture_files) - 1))
    return texture_choose


def generate_object(p_data,
                    p_scene,
                    p_config,
                    p_index_object,
                    p_iteration,
                    p_textures_choose):
    """
    Function that will create a object in the scene.
    :param p_data: Data need to create the object (name, x, y, z, rotation_need, configuration)
    :param p_scene: Scene
    :param p_config: Config
    :param p_index_object index of the object
    :param p_iteration iteration
    :param p_textures_choose: array of texture
    :return:
    """
    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    new_obj = bpy.context.object
    new_obj.select = True
    new_obj.name = p_data[0]
    new_obj.scale = p_config["height"], p_config["width"], p_config["weight"]
    new_obj.location = [p_data[1], p_data[2], p_data[3]]
    p_scene.objects.active = new_obj
    new_obj[("%s" % VIRTUAL_OBJECT)] = VIRTUAL_OBJECT
    new_obj[("%s" % CONFIGURATION_OBJECT)] = p_data[5]
    bpy.context.scene.objects.active.pass_index = p_index_object
    if p_data[4]:
        new_obj.rotation_euler.rotate_axis("Z", radians(90))
    # bpy.ops.rigidbody.object_add(type="ACTIVE")
    # bpy.context.object.rigid_body.collision_shape = 'CONVEX_HULL'
    bpy.ops.object.mode_set(mode='EDIT')
    make_rotation_through_x = random.randint(0, 1) == 0 if False else True
    if make_rotation_through_x:
        new_obj.rotation_euler.rotate_axis("X", radians(180))

    texture_index = p_textures_choose[p_data[6]]
    add_texture_to_object(p_data[0],
                          str(p_index_object),
                          str(p_iteration),
                          root_path_texture
                          + "\\"
                          + g_texture_files[texture_index])

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    if p_config["deformation"]:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(new_obj.data)
        bmesh.ops.subdivide_edges(bm,
                                  seed=42,
                                  edges=bm.edges,
                                  use_grid_fill=True,
                                  cuts=50)

        if g_debugMode is False:
            random_isotropic_scaling = random.randint(0, 1)
            random_anisotropic_scaling = random.randint(0, 1)
        else:
            random_isotropic_scaling = 1
            random_anisotropic_scaling = 1

        options = (True,
                   True,  # Cast cylinder
                   True,  # cast Sphere
                   False,  # Bevel modifier (slow a lot without nothing changes) # Need to investigate
                   True,  # Twist
                   False,  # Bend
                   False,  # Taper
                   (random_isotropic_scaling == 0) if False else True,
                   (random_anisotropic_scaling == 0) if False else True)

        bpy.ops.object.mode_set(mode='OBJECT')

        add_deformations(new_obj,
                         p_scene,
                         0.99,
                         1.11,
                         options)

    return p_textures_choose


def delete_old_object_from_scene(p_scene):
    """
    Delete all the previous object from the scene
    Exception on two object MODEL and GROUND that are object that will be as reference
    Camera and lamp are not concern
    :param p_scene scene
    :return:
    """
    object_to_delete = False
    # Delete objects by type
    for o in p_scene.objects:
        if bpy.context.active_object is not None:
            bpy.ops.object.mode_set(mode='OBJECT')
        if o.type == 'MESH':
            o.select = True
            object_to_delete = True
        elif o.type != 'CAMERA':
            o.select = True
        else:
            o.select = False

    # Call the operator only once
    if object_to_delete:
        bpy.ops.object.delete()


def un_select_all_object(p_scene):
    """
    Function that will un select all the object
    :param p_scene : current_scene
    :return:
    """
    for o in p_scene.objects:
        o.select = False


def generate_image_folder(p_path):
    intermediate_folder = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    full_path = os.path.join(p_path, intermediate_folder)
    if not os.path.exists(full_path):
        os.mkdir(full_path)
    return full_path


def picture_capture(p_camera, p_path, p_nb_level, p_folder_scenario, p_config, p_scene):
    """
    This method will allow to capture the view from the camera
    :param p_scene: scene
    :param p_camera : Camera on the scene
    :param p_path: path where we will store the data
    :param p_nb_level: number of level
    :param p_folder_scenario path for storing data
    :param p_config : configuration
    :return:
    """
    step_count = p_nb_level * p_config["nbCubeByLevel"] + 1
    counter_level = p_nb_level - 1
    print(counter_level)
    brick_random_to_remove = list(range(6))
    random.shuffle(brick_random_to_remove)
    for step in range(1, step_count + 1):
        if counter_level >= 0:
            full_path = generate_image_folder(p_path + p_folder_scenario + '\\')
            
            render_camera(bpy.context,
                          p_camera,
                          full_path,
                          p_config["pattern_name_file_save"] % (step, p_scene.objects[
                              p_config["pattern_layer"] % (counter_level, brick_random_to_remove[step % 6])][
                              CONFIGURATION_OBJECT]),
                          p_use_gpu=p_config["use_gpu"])
            p_scene.objects[p_config["pattern_layer"] % (counter_level, brick_random_to_remove[step % 6])].select = True
            bpy.ops.object.delete()
        if step % 6 == 0:
            counter_level -= 1
            # the camera will "follow" the removing of the brick
            random.shuffle(brick_random_to_remove)


def save_scenario_data(p_path,
                       p_folder_scenario,
                       p_objects_params,
                       p_generation_configuration,
                       p_textures_choose,
                       p_config):
    """
    Save the data from the current scenario
    :param p_path: path of where the file will be stored
    :param p_folder_scenario path for storing data
    :param p_objects_params list of all object created
    :param p_generation_configuration  disparity of the configuration
    :param p_textures_choose : id of texture choose
    :param p_config configuration of the scenario
    :return:
    """
    with open(p_path + p_folder_scenario + '\\scenario.txt', 'w') as scenario_txt_handler:
        scenario_txt_handler.write("name, "
                                   "position_x, "
                                   "position_y, "
                                   "position_z, "
                                   "rotation_needed, "
                                   "configuration, "
                                   "index_texture\n")
        for item in p_objects_params:
            scenario_txt_handler.write("(%s, %s, %s, %s, %s, %s, %s)\n" % (item[0],
                                                                           item[1],
                                                                           item[2],
                                                                           item[3],
                                                                           item[4],
                                                                           item[5],
                                                                           item[6]))
    # Save the scenario_data file that is link to this scenario
    with open(p_path + p_folder_scenario + '\\scenario_data.txt', 'w') as scenario_txt_data_handler:
        data = Counter(p_generation_configuration)
        scenario_txt_data_handler.write("(%s)\n" % (str(data)))
        scenario_txt_data_handler.write("(%s)\n" % (str(p_textures_choose)))

    # Save the config file that is link to this scenario
    with open(p_path + p_folder_scenario + '\\config.json', 'w') as json_file:
        json.dump(p_config, json_file)
        json_file.close()


def reset_data(p_scene):
    """
    Reset all the data on the scene
    :param p_scene: blender scene
    :return:
    """
    un_select_all_object(p_scene)
    delete_old_object_from_scene(p_scene)


def iteration_runner(p_config,
                     p_number_level,
                     p_replay_mode=False,
                     p_objects_params=None,
                     p_texture_choose=None,
                     p_iteration_number=None):
    """
    Iteration Runner
    Function that will run the scenario
    :param p_config: configuration
    :param p_number_level: nb of leve
    :param p_replay_mode: is this function is started by the replay mode
    :param p_objects_params: Array that contains object params for the scene creation.
    Not none if this function is call by the replay mode
    :param p_texture_choose: Array that contains textures id  for the scene creation.
    Not none if this function is call by the replay mode
    :param p_iteration_number: Number of iteration
    :return:
    """

    if p_objects_params is None:
        p_objects_params = []
    if p_texture_choose is None:
        p_texture_choose = []
    if p_iteration_number is None:
        iteration_number = p_config["iterationNumber"]
    else:
        iteration_number = p_iteration_number
    nb_configuration_available = p_config["nbConfigurationAvailable"]
    weight = p_config["weight"]
    separator = p_config["separator"]
    a_scene = bpy.context.scene
    for iteration in range(iteration_number):

        print("=============================================")
        print("==============Iteration     %s================" % str(iteration))
        print("==============Initialisation ================")
        initialize_scene()
        a_scene.render.resolution_x = 1280
        a_scene.render.resolution_y = 1024
        a_scene.render.resolution_percentage = 100
        print("=============================================")
        folder_scenario = generate_folder_scenario(iteration)
        if g_debugMode is False and not os.path.exists(p_config["root_path_data"] + folder_scenario):
            os.mkdir(p_config["root_path_data"] + folder_scenario)

        areas = [a_scene.objects["Lamp1"],
                 a_scene.objects["Lamp2"]]
        camera = a_scene.objects["Camera"]
        camera.location = [0,
                           0,
                           27]

        camera.rotation_euler = [0,
                                 0,
                                 radians(90)]

        bpy.data.cameras[camera.name].lens = 8
        bpy.data.cameras[camera.name].clip_start = 5
        bpy.data.cameras[camera.name].clip_end = 150
        bpy.data.cameras[camera.name].sensor_fit = 'AUTO'
        bpy.data.cameras[camera.name].sensor_width = 8

        # delete_old_object_from_scene(a_scene)
        objects_params = p_objects_params.copy()
        configuration_generation = []
        textures_choose = p_texture_choose.copy()
        # If debug mode is activated we generate always the same configuration
        # and only one level.
        # It allow to have always the same data in order to compare

        if p_replay_mode is False:
            textures_choose = generate_texture_array(p_config)
            if g_debugMode:
                for i in range(1):
                    configuration_generation.append(1)
                    objects_params = generate_configuration(10,
                                                            i,
                                                            p_config,
                                                            objects_params)
            else:
                for i in range(p_number_level):
                    layer_configuration = random.randint(0,
                                                         nb_configuration_available - 1)
                    configuration_generation.append(layer_configuration)
                    objects_params = generate_configuration(layer_configuration,
                                                            i,
                                                            p_config,
                                                            objects_params)

                save_scenario_data(p_path=root_path_data,
                                   p_folder_scenario=folder_scenario,
                                   p_objects_params=objects_params,
                                   p_generation_configuration=configuration_generation,
                                   p_textures_choose=textures_choose,
                                   p_config=p_config)

        if p_replay_mode or p_config["scriptGeneration"] is False:
            # Generate object into the scene
            for index_object in range(len(objects_params)):
                generate_object(p_data=objects_params[index_object],
                                p_scene=a_scene,
                                p_config=p_config,
                                p_index_object=len(objects_params) - index_object,
                                p_iteration=iteration,
                                p_textures_choose=textures_choose)
            un_select_all_object(a_scene)
            print("NbObject : {}".format(g_nb_objects))
            if g_debugMode is False:
                picture_capture(p_camera=camera, p_path=root_path_data, p_nb_level=nbLevel,
                                p_folder_scenario=folder_scenario, p_config=p_config, p_scene=a_scene)
        reset_data(a_scene)
        create_end_file(root_path_data, folder_scenario)


def create_end_file(p_path, p_folder_scenario):
    """
    Create a file that will indicate if the process blender is finished.
    :param p_path:
    :param p_folder_scenario:
    :return:
    """
    with open(p_path + p_folder_scenario + '\\OK.txt', 'w') as end_file:
        end_file.write("OK")
        end_file.close()


def replay_runner(p_config):
    """
    Replay mode
    This function will replay scenario
    :param p_config: configuration
    :return:
    """
    path_replay_mode = p_config["pathReplay"]
    # get the variable root folder
    # is true that means we have three file :
    # scenario.txt
    # scenario_data.txt
    # config.json
    is_root_folder = p_config["isRootFolderReplayMode"]
    if is_root_folder:
        process_replay_mode_folder(path_replay_mode)
    else:
        for root, dirs, files in os.walk(path_replay_mode):
            if "scenario.txt" in str(files) and "config.json" in str(files) and "scenario_data.txt" in str(files):
                process_replay_mode_folder(root, p_iteration_number=1)


def process_replay_mode_folder(p_path_replay_mode,
                               p_iteration_number=None):
    """
    Process with the replay mode a folder
    This folder must contains scenario.txt, scenario_data.txt, and config.json
    :param p_path_replay_mode: path to the folder to process in replay mode
    :param p_iteration_number: number of iteration
    :return:
    """
    object_params = []
    with open(os.path.join(p_path_replay_mode, 'config.json')) as config_file:
        scenario_config = json.load(config_file)
    with open(os.path.join(p_path_replay_mode, "scenario.txt")) as scenario_txt_file:
        next(scenario_txt_file)
        for line in scenario_txt_file:
            temp_line = line[1:-2]
            data = temp_line.split(",")
            object_params.append((data[0],
                                  float(data[1]),
                                  float(data[2]),
                                  float(data[3]),
                                  strtobool(data[4].strip().lower()),
                                  int(data[5]),
                                  int(data[6])))
    with open(os.path.join(p_path_replay_mode, "scenario_data.txt")) as scenario_data_file:
        next(scenario_data_file)
        for line in scenario_data_file:
            texture_choose = list(map(int, line[2:-3].split(",")))
    iteration_runner(p_config=scenario_config,
                     p_number_level=scenario_config["nbLevel"],
                     p_replay_mode=True,
                     p_objects_params=object_params,
                     p_texture_choose=texture_choose,
                     p_iteration_number=p_iteration_number)


def initialize_scene():
    # Change the render engine
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.render.image_settings.color_depth = '16'
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.cycles.max_bounces = 12
    bpy.context.scene.cycles.use_square_samples = False
    bpy.context.scene.cycles.preview_samples = 32
    bpy.context.scene.cycles.samples = 256
    bpy.context.scene.cycles.device = 'GPU'


    texture_index = random.randint(0, len(g_texture_files_box) - 1)
    path_texture_box = root_path_texture_box + "\\" + g_texture_files_box[texture_index]
    delete_old_object_from_scene(bpy.context.scene)
    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    left_border = bpy.context.object
    left_border.name = "LEFT_BORDER"
    left_border.scale = [1, 1, 1]
    left_border.dimensions = [0.5, 15, 8]
    left_border.location = [-5.0, 0, 3.9]
    add_texture_to_object(left_border.name, 4005, 4005, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    # left_border.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    right_border = bpy.context.object
    right_border.name = "RIGHT_BORDER"
    right_border.scale = [1, 1, 1]
    right_border.dimensions = [0.5, 15, 8]
    right_border.location = [+5.0, 0, 3.9]

    add_texture_to_object(right_border.name, 4004, 4004, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    # right_border.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    bottom_border = bpy.context.object
    bottom_border.name = "BOTTOM_BORDER"
    bottom_border.scale = [1, 1, 1]
    bottom_border.dimensions = [11.25, 0.5, 8]
    bottom_border.location = [0, -7, 3.9]
    add_texture_to_object(bottom_border.name, 4003, 4003, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    # bottom_border.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    top_border = bpy.context.object
    top_border.name = "TOP_BORDER"
    top_border.scale = [1, 1, 1]
    top_border.dimensions = [11.25, 0.5, 8]
    top_border.location = [0, +7, 3.9]
    add_texture_to_object(top_border.name, 4002, 4002, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')
    # top_border.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    ground = bpy.context.object
    ground.name = "GROUND"
    ground.scale = [1, 1, 1]
    ground.dimensions = [11.25, 15, 0.5]

    add_texture_to_object(ground.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    # ground.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    potence = bpy.context.object
    potence.name = "POTENCE"
    potence.scale = [1, 1, 10.5]
    potence.dimensions = [2, 2, 28]
    potence.location = [-9, 0, 14]

    add_texture_to_object(potence.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    arm_potence = bpy.context.object
    arm_potence.name = "ARM_POTENCE"
    arm_potence.scale = [4, 0.5, 0.5]
    arm_potence.dimensions = [8, 1, 1]
    arm_potence.location = [-4.5, 0, 27.5]

    add_texture_to_object(arm_potence.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    i_core = bpy.context.object
    i_core.name = "I_CORE"
    i_core.scale = [0.5, 3.5, 0.5]
    i_core.dimensions = [1, 7, 1]
    i_core.location = [0, 0, 27.5]

    add_texture_to_object(i_core.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    i_branch_1 = bpy.context.object
    i_branch_1.name = "I_BRANCH_1"
    i_branch_1.scale = [2, 0.5, 0.5]
    i_branch_1.dimensions = [4, 1, 1]
    i_branch_1.location = [0, -3.5, 27.5]

    add_texture_to_object(i_branch_1.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cube_add(radius=1, location=[0, 0, 0])
    i_branch_2 = bpy.context.object
    i_branch_2.name = "I_BRANCH_2"
    i_branch_2.scale = [2, 0.5, 0.5]
    i_branch_2.dimensions = [4, 1, 1]
    i_branch_2.location = [0, 3.5, 27.5]

    add_texture_to_object(i_branch_2.name, 4001, 4001, path_texture_box)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    # ground.select = True
    bpy.ops.rigidbody.object_add(type="PASSIVE")

    # Create new lamp datablock
    lamp_data = bpy.data.lamps.new(name="Lamp1", type='AREA')
    lamp_data.shape = 'RECTANGLE'
    lamp_data.energy = 100
    lamp_data.size = 1
    lamp_data.size_y = 12
    lamp_data.cycles.max_bounces = 1024
    # Create new object with our lamp datablock
    lamp_object = bpy.data.objects.new(name="Lamp1", object_data=lamp_data)
    # Link lamp object to the scene so it'll appear in this scene
    bpy.context.scene.objects.link(lamp_object)
    lamp_object.location = [1.5, 0, 27]
    bpy.data.lamps[lamp_data.name].use_nodes = True
    bpy.data.lamps[lamp_data.name].node_tree.nodes["Emission"].inputs[1].default_value = 3000
    # lamp_object.rotation_euler.rotate_axis("X", radians(-30))

    # Create new lamp datablock
    lamp_data = bpy.data.lamps.new(name="Lamp2", type='AREA')
    lamp_data.shape = 'RECTANGLE'
    lamp_data.energy = 100
    lamp_data.size = 1
    lamp_data.size_y = 12
    lamp_data.cycles.max_bounces = 1024
    # Create new object with our lamp datablock
    lamp_object = bpy.data.objects.new(name="Lamp2", object_data=lamp_data)
    # Link lamp object to the scene so it'll appear in this scene
    bpy.context.scene.objects.link(lamp_object)
    lamp_object.location = [-1.5, 0, 27]
    bpy.data.lamps[lamp_data.name].use_nodes = True
    bpy.data.lamps[lamp_data.name].node_tree.nodes["Emission"].inputs[1].default_value = 3000
    un_select_all_object(bpy.context.scene)


if __name__ == '__main__':

    # Load configuration JSON file that contains all the configuration for the scenarii
    with open('D:\\Simulator\\config.json') as f:
    #with open('C:\\Users\\k.giroux\\Documents\\blender\\config.json') as f:
        config = json.load(f)
        print("=============================================")
        print(config)
        print("=============================================")

    print("=============================================")
    print("* Simulator's Version : ", config["nVersion"])
    g_debugMode = config["debugMode"]
    print("* Debug Mode : ", g_debugMode)
    root_path = config["root_path"]
    print("* Root Path : ", root_path)
    root_path_texture = root_path + config["root_path_texture_directory"]
    root_path_texture_box = root_path + config["root_path_texture_directory_box"]
    print("* Root Path Texture: ", root_path_texture)
    root_path_data = config["root_path_data"]
    print("* Root Path Data: ", root_path_data)
    iteration_mode = config["iterationMode"]
    print("* Iteration Mode : ", iteration_mode)
    replay_mode = config["replayMode"]
    print("* Replay Mode : ", replay_mode)
    g_texture_files = [pos_img
                       for pos_img in os.listdir(root_path_texture)
                       if pos_img.endswith('.jpg')]
    g_texture_files_box = [pos_img
                       for pos_img in os.listdir(root_path_texture_box)
                       if pos_img.endswith('.jpg')]
    print("* Number of texture file detected: ", len(g_texture_files))
    print("* Number of texture file detected for box: ", len(g_texture_files_box))
    print("=============================================")
    g_nb_objects = config["nbCubeByLevel"] *  config["nbLevel"] * 2
    # defined some caracteristic for the debug mode.
    if g_debugMode:
        picture_enabled = False
        nbLevel = 1
        deformations = True
    else:
        picture_enabled = True
        nbLevel = config["nbLevel"]
        deformations = True

    if iteration_mode and replay_mode:
        print("ERROR : Invalid Configuration : Iteration Mode can't be activated with the replay mode")
        exit(-1)

    if iteration_mode is False and replay_mode is False:
        print("ERROR : No mode activated. If you want to run only one, "
              "activate the iteration mode and set the iteration value to 1")
        exit(-1)

    if iteration_mode:
        iteration_runner(config, nbLevel)
    if replay_mode:
        replay_runner(config)
