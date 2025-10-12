bl_info = {
    "name": "Smart 2D Animation Workflow",
    "description": "Generalized 2D animation tools including Smart Bones, bendy parts, expressions, depth, automation, colouring, layering, hybrid animation, and experimental AI tweening",
    "author": "Lowena Cove",
    "version": (0, 4, 0),
    "blender": (4, 0, 0),
    "location": "3D View > Smart Bones",
    "warning": "Requires FILM/TensorFlow or ToonCrafter/Torch for AI tweening; use install operator to auto-setup dependencies. Assumes ffmpeg installed for frame extraction.",
    "wiki_url": "https://github.com/sketchy-squirrel/smart-bones",
    "category": "Rigging"
}

import bpy
import re
import os
import subprocess
import sys
import tempfile
import threading
from bpy.types import PropertyGroup
from bpy.props import CollectionProperty

#---------------------------------------------------------------------
#    Properties
#---------------------------------------------------------------------

class ColorItem(PropertyGroup):
    color : bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )

class SmartBoneProperties(bpy.types.PropertyGroup):
    
    # Original properties...
    armature_name : bpy.props.StringProperty(
        name = "Target",
        description = "Control Armature",
    )
    
    control_name : bpy.props.StringProperty(
        name = "Control",
        description = "Control Bone",
    )
    
    transform_channel : bpy.props.EnumProperty(
        name = "Channel",
        description = "Control Axis",
        items = [
                ('LOCATION_X', 'LOCATION_X',""),
                ('LOCATION_Y', 'LOCATION_Y',""),
                ('LOCATION_Z', 'LOCATION_Z',""),
                ('ROTATION_X', 'ROTATION_X',""),
                ('ROTATION_Y', 'ROTATION_Y',""),
                ('ROTATION_Z', 'ROTATION_Z',""),
                ('SCALE_X', 'SCALE_X',""),
                ('SCALE_Y', 'SCALE_Y',""),
                ('SCALE_Z', 'SCALE_Z',""),   
            ],
        default = 'LOCATION_X'
    )
    
    target_space : bpy.props.EnumProperty(
        name = "Space",
        description = "Transform Space",
        items =[
            ('WORLD', 'WORLD', ""),
            ('CUSTOM', 'CUSTOM', ""),
            ('LOCAL', 'LOCAL', "")
        ],
        default = 'LOCAL'
            
    )
    
    space_object_name : bpy.props.StringProperty(
        name = "Space Object",
        description = "Takes local space from another object, to apply to constraint",
        default = "",
    )
    
    space_subtarget : bpy.props.StringProperty(
        name = "Space Subtarget",
        description = "Custom space target, if 'Space Object' is of type ARMATURE",
        default = "",
    )
    
    transform_min : bpy.props.FloatProperty(
    name = "Min Transform Range",
    description = "Minimum Transform Value",
    default = 0.0,
    )
    
    transform_max : bpy.props.FloatProperty(
    name = "Max Transform Range",
    description = "Maximum Transform Value",
    default = 1.0,
    )
    
    action_name : bpy.props.StringProperty(
    name = "Action",
    description = "Name of affected action",
    )
    
    frame_min : bpy.props.IntProperty(
    name = "Min Frame",
    description = "Start Frame of Action",
    default = 0,
    )
    
    frame_max : bpy.props.IntProperty(
    name = "Max Frame",
    description = "End Frame of Action",
    default = 20,
    )

    # New properties for Bendy Body Parts
    lattice_resolution : bpy.props.IntProperty(
        name = "Lattice Resolution",
        description = "Resolution in W direction for lattice",
        default = 64,
        min = 1,
        max = 64
    )

    bone_segments : bpy.props.IntProperty(
        name = "Bone Segments",
        description = "Bendy bone segments",
        default = 32,
        min = 1,
        max = 64
    )

    exclude_layers : bpy.props.StringProperty(
        name = "Exclude Layers",
        description = "Comma-separated layer names to exclude from deformation",
        default = ""
    )

    # New for Better Expressions
    expression_type : bpy.props.EnumProperty(
        name = "Expression Type",
        description = "Type of facial asset",
        items = [
            ('EYES', 'Eyes', ""),
            ('MOUTH', 'Mouth', ""),
            ('BROWS', 'Brows', "")
        ],
        default = 'EYES'
    )

    num_variations : bpy.props.IntProperty(
        name = "Number of Variations",
        description = "Number of expression assets to create",
        default = 3,
        min = 1
    )

    tween_frames : bpy.props.IntProperty(
        name = "Tween Frames",
        description = "Frames for tweening between expressions",
        default = 5,
        min = 1
    )

    # New for Some Depth
    use_depth : bpy.props.BoolProperty(
        name = "Use Depth",
        description = "Enable optional depth for selected parts",
        default = False
    )

    depth_offset : bpy.props.FloatProperty(
        name = "Depth Offset",
        description = "Z-depth offset for parallax",
        default = 0.0
    )

    parallax_strength : bpy.props.FloatProperty(
        name = "Parallax Strength",
        description = "Strength of parallax effect",
        default = 1.0
    )

    # New for Automation
    preset_type : bpy.props.EnumProperty(
        name = "Preset",
        description = "Automation preset",
        items = [
            ('ARM_BENDY', 'Arm Bendy', ""),
            ('LEG_BENDY', 'Leg Bendy', ""),
            ('FACE_EXPRESSIONS', 'Face Expressions', ""),
            ('FULL_BODY', 'Full Body Rig', "")
        ],
        default = 'ARM_BENDY'
    )

    # New for Easier Colouring
    color_palette : CollectionProperty(type=ColorItem)

    fill_type : bpy.props.EnumProperty(
        name = "Fill Type",
        description = "Type of colouring",
        items = [
            ('FILL', 'Fill', ""),
            ('SHADE', 'Shade', "")
        ],
        default = 'FILL'
    )

    # New for Auto-layering
    group_layers : bpy.props.BoolProperty(
        name = "Group Layers",
        description = "Link/group layers as Smart Object",
        default = False
    )

    linked_group_name : bpy.props.StringProperty(
        name = "Group Name",
        description = "Name for linked layer group",
        default = "SmartGroup"
    )

    # New for AI Tweening
    interpolator_type : bpy.props.EnumProperty(
        name = "Interpolator",
        description = "Frame interpolation model",
        items = [
            ('FILM', 'FILM', ""),
            ('TOONCRAFTER', 'ToonCrafter', "")
        ],
        default = 'FILM'
    )

    film_path : bpy.props.StringProperty(
        name = "FILM Path",
        description = "Path to FILM installation directory",
        subtype='DIR_PATH',
        default = ""
    )

    tooncrafter_path : bpy.props.StringProperty(
        name = "ToonCrafter Path",
        description = "Path to ToonCrafter installation directory",
        subtype='DIR_PATH',
        default = ""
    )

    model_path : bpy.props.StringProperty(
        name = "Model Path",
        description = "Path to pre-trained model (FILM: saved_model dir, ToonCrafter: model.ckpt)",
        subtype='FILE_PATH',
        default = ""
    )

    ai_prompt : bpy.props.StringProperty(
        name = "AI Prompt",
        description = "Prompt for generative interpolation (used in ToonCrafter)",
        default = "a cartoon animation"
    )

    ai_times_to_interpolate : bpy.props.IntProperty(
        name = "AI Interpolations",
        description = "Number of intermediate frames to generate",
        default = 1,
        min = 1
    )

#---------------------------------------------------------------------
#    Operators
#---------------------------------------------------------------------

# Original operators...
class POSE_OT_AddSmartBone(bpy.types.Operator):
    """Add action constraints to all bones in action"""
    bl_idname = "myops.add_smart_bone"
    bl_label = "Add Smart Bone"
    
    
    def execute(self, context):
        
        current_object = bpy.context.object
        
        smart_bone_tool = context.scene.smart_bone_tool
        
        #Find Action Bones
        action = bpy.data.actions[smart_bone_tool.action_name]
        action_bones = self.find_action_bones(action)
        
            
        #make all bone layers visible
        current_selection = []
        obj = context.scene.objects[smart_bone_tool.armature_name]
        if obj.type == "ARMATURE":
            armature_data = obj.data
        
        
        #Add final constraints
        self.add_action_constraint(
            current_object,
            smart_bone_tool.armature_name,
            action_bones,
            smart_bone_tool.control_name,
            smart_bone_tool.transform_channel,
            smart_bone_tool.target_space,
            smart_bone_tool.space_object_name,
            smart_bone_tool.space_subtarget,
            [smart_bone_tool.transform_min, smart_bone_tool.transform_max],
            smart_bone_tool.action_name,
            [smart_bone_tool.frame_min, smart_bone_tool.frame_max],
        )


        return ({'FINISHED'})
    
    def find_action_bones(self, action):                                        # create a list of bones used in the action in armature
        
        bones = []
        
        for fcurve in action.fcurves:
            fcurve_name = str(fcurve.data_path)
            if "pose.bones" in fcurve_name:                                         # only process keyframes on pose bones, not armature or objects.
                action_bone = re.findall('"([^"]*)"', fcurve.data_path)[0]          # find bone for each key in action        
                if action_bone not in bones:                                        # add found bone to bones if not already present
                    bones.append(action_bone)
        
        return(bones)
    
    
    def add_action_constraint(self, current_object, ctrl_armature_name, action_bones, control_name, transform_channel, target_space, space_obj, space_sub, transform_range, action_name, frame_range):
        
        
        if current_object.type == 'ARMATURE':
            
            #enter pose mode
            bpy.ops.object.mode_set(mode='POSE')
        
            #stores list of bones as string, to check if affected bone is in current object
            bones_in_current_obj = []
            for i in current_object.pose.bones:
              bones_in_current_obj.append(i.name)
            
            
            for action_bone in action_bones:
                    
                    #Prevents trying to add constraint to bone in another armature
                    if action_bone in bones_in_current_obj:
                    
                        current_bone = current_object.pose.bones[action_bone]
                    
                        if bpy.data.objects[ctrl_armature_name].pose.bones[control_name] != current_bone: #prevents adding a constraint to a bone, targeting its self
                    
                            constraint_name = str("SB_"+control_name+"_"+action_name)
                            
                            constraint_exists = False
                            # Test if bone constraint already exists
                            for constraint in current_bone.constraints:
                                if constraint.name == constraint_name:
                                    constraint_exists = True
                            
                            if constraint_exists == False:
                                constraint = current_bone.constraints.new("ACTION")
                                constraint.name = constraint_name
                            
                            constraint.target = bpy.data.objects[ctrl_armature_name]
                            constraint.subtarget = control_name
                            constraint.transform_channel = transform_channel
                            constraint.target_space = target_space
                            
                            if target_space == "CUSTOM":
                                try:
                                    constraint.space_object = bpy.data.objects[space_obj]
                                    
                                    if space_obj != "" and bpy.context.objects[space_obj].type == "ARMATURE":
                                        constraint.space_subtarget = space_sub
                                        
                                except:
                                    constraint.target_space = "LOCAL"
                                    
                            constraint.min = transform_range[0]
                            constraint.max = transform_range[1]
                            constraint.action = bpy.data.actions[action_name]
                            constraint.frame_start = frame_range[0]
                            constraint.frame_end = frame_range[1]


class POSE_OT_DeleteSmartBone(bpy.types.Operator):
    """Delete relevant action constraints within selected armature"""
    
    bl_idname = "myops.delete_smart_bone"
    bl_label = "Delete Smart Bone"
    
    
    def execute(self, context):
        
        current_armature = bpy.context.object
        
        if current_armature.type == "ARMATURE":
            
            smart_bone_tool = context.scene.smart_bone_tool
            
            armature_name = smart_bone_tool.armature_name
            control_name = smart_bone_tool.control_name
            action_name = smart_bone_tool.action_name
            
            constraint_name = str("SB_"+control_name+"_"+action_name)
            
            bpy.ops.object.mode_set(mode='POSE')
        
            #select all the bones in armature
                
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.select_all(action='DESELECT')
            
            #make all bone layers visible
            current_selection = []
            obj = context.scene.objects[smart_bone_tool.armature_name]
            if obj.type == "ARMATURE":
                armature_data = obj.data
                
                    
            
            for bone in current_armature.data.edit_bones:
                bone.select = True
            
            #remove_constraints
            for bone in current_armature.pose.bones:
                for constraint in bone.constraints:
                    if constraint_name in constraint.name:
                        bone.constraints.remove(constraint)
            
            bpy.ops.object.mode_set(mode='POSE')
            
            return {'FINISHED'}

# New Operator for Installing AI Dependencies
class POSE_OT_InstallAIDeps(bpy.types.Operator):
    """Install AI dependencies for FILM and ToonCrafter"""
    bl_idname = "myops.install_ai_deps"
    bl_label = "Install AI Deps"

    def execute(self, context):
        def install():
            python_exe = sys.executable
            addon_dir = os.path.dirname(__file__)
            libs_dir = os.path.join(addon_dir, "libs")
            os.makedirs(libs_dir, exist_ok=True)

            # Ensure pip
            subprocess.call([python_exe, '-m', 'ensurepip', '--upgrade'])
            subprocess.call([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'])

            # Common packages
            packages = ['tensorflow', 'torch', 'diffusers', 'transformers', 'accelerate', 'mediapy', 'numpy', 'scikit-image', 'pyyaml', 'natsort']
            subprocess.call([python_exe, '-m', 'pip', 'install'] + packages)

            # Clone and install FILM
            film_dir = os.path.join(libs_dir, "frame-interpolation")
            if not os.path.exists(film_dir):
                subprocess.call(['git', 'clone', 'https://github.com/google-research/frame-interpolation', film_dir])
            subprocess.call([python_exe, '-m', 'pip', 'install', '-r', os.path.join(film_dir, 'requirements.txt')])

            # Clone and install ToonCrafter
            tooncrafter_dir = os.path.join(libs_dir, "ToonCrafter")
            if not os.path.exists(tooncrafter_dir):
                subprocess.call(['git', 'clone', 'https://github.com/Doubiiu/ToonCrafter', tooncrafter_dir])
            subprocess.call([python_exe, '-m', 'pip', 'install', '-r', os.path.join(tooncrafter_dir, 'requirements.txt')])

        threading.Thread(target=install).start()
        self.report({'INFO'}, "Installing AI dependencies in background... This may take a while.")
        return {'FINISHED'}

# New Operators

class POSE_OT_AddBendyPart(bpy.types.Operator):
    """Add lattice-based bendy deformation to selected GP part"""
    bl_idname = "myops.add_bendy_part"
    bl_label = "Add Bendy Part"

    def execute(self, context):
        obj = context.object
        if obj.type != 'GPENCIL':
            self.report({'ERROR'}, "Select a Grease Pencil object")
            return {'CANCELLED'}

        tool = context.scene.smart_bone_tool

        # Create Lattice
        bpy.ops.object.lattice_add()
        lattice = context.object
        lattice.name = "Bendy_Lattice"
        lattice.data.points_w = tool.lattice_resolution
        bbox_min = obj.bound_box[0]
        bbox_max = obj.bound_box[6]
        lattice.location = obj.location
        lattice.scale = (bbox_max[0] - bbox_min[0], bbox_max[1] - bbox_min[1], 1)  # Fit to X/Y

        # Create Armature
        bpy.ops.object.armature_add()
        armature = context.object
        armature.name = "Bendy_Armature"
        bpy.ops.object.mode_set(mode='EDIT')
        bone1 = armature.data.edit_bones[0]
        bone1.head = (0, 0, 0)
        bone1.tail = (0, 0.5, 0)
        bone2 = armature.data.edit_bones.new("Bone.001")
        bone2.head = bone1.tail
        bone2.tail = (0, 1, 0)
        bone3 = armature.data.edit_bones.new("Bone.002")
        bone3.head = bone2.tail
        bone3.tail = (0, 1.5, 0)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Armature Modifier on Lattice
        mod = lattice.modifiers.new(type='ARMATURE', name="Armature")
        mod.object = armature

        # Vertex Groups on Lattice
        vg1 = lattice.vertex_groups.new(name="Bone")
        vg2 = lattice.vertex_groups.new(name="Bone.001")
        bpy.context.view_layer.objects.active = lattice
        bpy.ops.object.mode_set(mode='EDIT')
        # Simplified assignment: lower, mid, upper
        points = lattice.data.points
        num_points = len(points)
        for i, point in enumerate(points):
            if i < num_points / 3:
                lattice.vertex_groups.active_index = vg1.index
            elif i < 2 * num_points / 3:
                lattice.vertex_groups.active_index = vg2.index
            else:
                lattice.vertex_groups.active_index = lattice.vertex_groups["Bone.002"].index
            point.select = True
            bpy.ops.object.vertex_group_assign()
            point.select = False
        bpy.ops.object.mode_set(mode='OBJECT')

        # Lattice Modifier on GP
        mod_gp = obj.modifiers.new(type='GP_LATTICE', name="Lattice")
        mod_gp.object = lattice

        # Exclude layers
        exclude = tool.exclude_layers.split(',')
        vg_gp = obj.vertex_groups.new(name="Lattice")
        bpy.ops.object.mode_set(mode='EDIT_GPENCIL')
        for layer in obj.data.layers:
            if layer.info not in exclude:
                layer.select = True
                bpy.ops.gpencil.select_all(action='SELECT')
                vg_gp.assign()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Bendy Bones
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
        for bone in armature.pose.bones:
            bone.bbone_segments = tool.bone_segments
        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

class POSE_OT_AddExpressionAssets(bpy.types.Operator):
    """Add assets for better facial expressions with tweening"""
    bl_idname = "myops.add_expression_assets"
    bl_label = "Add Expression Assets"

    def execute(self, context):
        obj = context.object
        if obj.type != 'GPENCIL':
            self.report({'ERROR'}, "Select a Grease Pencil object")
            return {'CANCELLED'}

        tool = context.scene.smart_bone_tool
        gp = obj.data

        new_layers = []
        for i in range(tool.num_variations):
            layer_name = f"{tool.expression_type}_{i+1}"
            layer = gp.layers.new(name=layer_name, set_active=True)
            new_layers.append(layer)
            # Add placeholder stroke (simple circle for eyes/mouth)
            frame = layer.frames.new(context.scene.frame_current)
            stroke = frame.strokes.new()
            stroke.points.add(4)
            stroke.points[0].co = (-0.1, 0, 0)
            stroke.points[1].co = (0, 0.1, 0)
            stroke.points[2].co = (0.1, 0, 0)
            stroke.points[3].co = (0, -0.1, 0)

        # Setup tweening via shape keys or interpolate
        # For simplicity, add action for blending visibility
        if not gp.animation_data:
            gp.animation_data_create()
        action = bpy.data.actions.new("Expressions")
        gp.animation_data.action = action
        # Keyframe visibility for layers
        for layer in gp.layers:
            layer.hide = True
            layer.keyframe_insert(data_path="hide", frame=1)
        new_layers[0].hide = False
        new_layers[0].keyframe_insert(data_path="hide", frame=1)

        # Tween: Use interpolate for transitions
        context.scene.frame_set(1)
        bpy.ops.gpencil.interpolate_sequence(steps=tool.tween_frames)

        return {'FINISHED'}

class POSE_OT_AddDepth(bpy.types.Operator):
    """Add optional depth to selected parts"""
    bl_idname = "myops.add_depth"
    bl_label = "Add Depth"

    def execute(self, context):
        obj = context.object
        tool = context.scene.smart_bone_tool

        if tool.use_depth:
            if obj.type == 'GPENCIL':
                active_layer = obj.data.layers.active
                if active_layer:
                    # Offset layer z, but GP layers have no z, so object
                    obj.location.z += tool.depth_offset
            else:
                obj.location.z += tool.depth_offset

            # Parallax: Simple driver on object
            if bpy.context.scene.camera:
                driver = obj.driver_add("location", 2)  # Z
                driver.driver.type = 'SCRIPTED'
                driver.driver.expression = f"frame * {tool.parallax_strength / 100}"

        return {'FINISHED'}

class POSE_OT_ApplyPreset(bpy.types.Operator):
    """Apply automation preset"""
    bl_idname = "myops.apply_preset"
    bl_label = "Apply Preset"

    def execute(self, context):
        tool = context.scene.smart_bone_tool
        preset = tool.preset_type

        if preset == 'ARM_BENDY' or preset == 'LEG_BENDY':
            bpy.ops.myops.add_bendy_part()
        elif preset == 'FACE_EXPRESSIONS':
            bpy.ops.myops.add_expression_assets()
        # Add more for other presets, e.g., full body combines

        return {'FINISHED'}

class POSE_OT_AddColor(bpy.types.Operator):
    """Add a color to the palette"""
    bl_idname = "myops.add_color"
    bl_label = "Add Color"

    def execute(self, context):
        tool = context.scene.smart_bone_tool
        item = tool.color_palette.add()
        return {'FINISHED'}

class POSE_OT_EasyColour(bpy.types.Operator):
    """One-click colouring for GP objects"""
    bl_idname = "myops.easy_colour"
    bl_label = "Easy Colour"

    def execute(self, context):
        obj = context.object
        if obj.type != 'GPENCIL':
            self.report({'ERROR'}, "Select a Grease Pencil object")
            return {'CANCELLED'}

        tool = context.scene.smart_bone_tool
        gp = obj.data

        # Create new layer for colour
        color_layer = gp.layers.new(name="Color_Layer", set_active=True)

        # Fill selected strokes
        bpy.ops.object.mode_set(mode='EDIT_GPENCIL')
        bpy.ops.gpencil.fill()

        # Apply color from palette (use first for simplicity)
        if len(tool.color_palette) > 0:
            color = tool.color_palette[0].color
            mat = bpy.data.materials.new("Color_Mat")
            mat.grease_pencil.color = color
            index = len(gp.materials)
            gp.materials.append(mat)
            color_layer.material_index = index

        if tool.fill_type == 'SHADE':
            # Shade: Duplicate and offset for shadow
            bpy.ops.gpencil.duplicate()
            bpy.ops.gpencil.transform_translate(value=(0.01, 0.01, 0))

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

class POSE_OT_EditGroup(bpy.types.Operator):
    """Edit linked layer group"""
    bl_idname = "myops.edit_group"
    bl_label = "Edit Group"

    def execute(self, context):
        tool = context.scene.smart_bone_tool
        if tool.group_layers:
            # Simulate Smart Object: Unlock for edit
            obj = context.object
            for layer in obj.data.layers:
                if tool.linked_group_name in layer.info:
                    layer.lock = False
            bpy.ops.object.mode_set(mode='EDIT_GPENCIL')

        return {'FINISHED'}

class POSE_OT_AITween(bpy.types.Operator):
    """Experimental AI tweening using FILM or ToonCrafter"""
    bl_idname = "myops.ai_tween"
    bl_label = "Interpolate with AI"

    def execute(self, context):
        tool = context.scene.smart_bone_tool
        model_type = tool.interpolator_type

        if model_type == 'FILM':
            if not tool.film_path or not tool.model_path:
                self.report({'ERROR'}, "Set FILM and model paths")
                return {'CANCELLED'}
        elif model_type == 'TOONCRAFTER':
            if not tool.tooncrafter_path or not tool.model_path:
                self.report({'ERROR'}, "Set ToonCrafter and model paths")
                return {'CANCELLED'}

        obj = context.object
        if obj.type != 'GPENCIL':
            self.report({'ERROR'}, "Select Grease Pencil")
            return {'CANCELLED'}

        # Export current and next frame as PNG
        frame1 = context.scene.frame_current
        frame2 = frame1 + 1
        temp_dir = tempfile.mkdtemp()
        path1 = os.path.join(temp_dir, "frame1.png")
        path2 = os.path.join(temp_dir, "frame2.png")
        out_dir = os.path.join(temp_dir, "output")
        extract_dir = os.path.join(out_dir, "frames")
        os.makedirs(extract_dir, exist_ok=True)

        # Temp render setup
        original_cam = context.scene.camera
        bpy.ops.object.camera_add(location=(0,0,10))
        cam = context.object
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = 10  # Adjust as needed
        context.scene.camera = cam
        context.scene.render.filepath = path1
        bpy.ops.render.render(write_still=True)
        context.scene.frame_set(frame2)
        context.scene.render.filepath = path2
        bpy.ops.render.render(write_still=True)
        context.scene.camera = original_cam
        bpy.data.objects.remove(cam)

        if model_type == 'FILM':
            # Call FILM interpolator_cli
            cmd = [
                sys.executable, "-m", "frame_interpolation.interpolator_cli",
                "--pattern", temp_dir + "/frame*.png",
                "--model_path", tool.model_path,
                "--times_to_interpolate", str(tool.ai_times_to_interpolate),
                "--output_video", os.path.join(out_dir, "interp.mp4")
            ]
            subprocess.run(cmd, cwd=tool.film_path)

            video_path = os.path.join(out_dir, "interp.mp4")

        elif model_type == 'TOONCRAFTER':
            # Create temp config yaml
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, 'w') as f:
                f.write(f"""
prompts:
  - "{tool.ai_prompt}"
image_path_1: "{path1}"
image_path_2: "{path2}"
video_length: {tool.ai_times_to_interpolate + 2}
width: 512
height: 320
fps: 8
use_ddpm: False
steps: 50
seed: 42
""")

            cmd = [
                sys.executable, "inference.py",
                "--config", config_path,
                "--savedir", out_dir,
                "--ckpt", tool.model_path,
                "--bs", "1",
                "--seed", "42"
            ]
            subprocess.run(cmd, cwd=tool.tooncrafter_path)

            video_path = os.path.join(out_dir, "samples", "sample_0", "video.gif")

        # Extract frames with ffmpeg
        subprocess.call(['ffmpeg', '-i', video_path, '-vf', 'fps=8', os.path.join(extract_dir, 'frame%03d.png')])

        # Import to Blender as image sequence reference
        bpy.ops.object.empty_add(type='IMAGE')
        empty = context.object
        empty.name = "AI_Interp_Seq"
        img = bpy.data.images.new("AIInterpSeq", 512, 320)
        img.source = 'SEQUENCE'
        img.directory = extract_dir
        img.filepath = os.path.join(extract_dir, 'frame001.png')
        empty.data = img
        empty.image_user.frame_duration = tool.ai_times_to_interpolate + 2
        empty.image_user.frame_start = 1
        empty.image_user.use_auto_refresh = True
        empty.empty_display_size = 5  # Adjust

        self.report({'INFO'}, f"AI interpolated frames imported as image sequence empty. Temp dir: {temp_dir}")
        return {'FINISHED'}

#---------------------------------------------------------------------
#    Panels
#---------------------------------------------------------------------

# Original Panel
class POSE_PT_SmartBonePanel(bpy.types.Panel):
    bl_label = "Smart Bone Panel"
    bl_idname = "POSE_PT_SmartBonePanel"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    #bl_context = "posemode"   

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        smart_bone_tool = scene.smart_bone_tool
        
        invalidInput = False
        
        #properties
        
        row = layout.row()
        
        row = layout.row()
        row.prop_search(smart_bone_tool, "armature_name", bpy.context.scene, "objects")
        
        row = layout.row()
        if context.scene.smart_bone_tool.armature_name != "":
            tgt_object = context.scene.objects[smart_bone_tool.armature_name]
            if tgt_object.type == "ARMATURE":
                row.prop_search(smart_bone_tool, "control_name", tgt_object.data, "bones")
                tgt_bone = context.scene.smart_bone_tool.control_name
            else:
                row.label(text = "Object Type = " + tgt_object.type, icon = "ERROR")
                invalidInput = True
        else:
            row.row().label(text="No selected Object", icon = "ERROR")
        
        row = layout.row()
        row.prop(smart_bone_tool, "transform_channel")
        row = layout.row()
        row.prop(smart_bone_tool, "target_space")
        
        row = layout.row()
        if smart_bone_tool.target_space == "CUSTOM":
            row.prop_search(smart_bone_tool, "space_object_name", context.scene, "objects")
            
            space_object = bpy.data.objects[smart_bone_tool.space_object_name]
            if space_object.type == "ARMATURE":
                row = layout.row()
                row.prop_search(smart_bone_tool, "space_subtarget", space_object.data, "bones")

        row = layout.row()
        row.label(text = 'Transform Range')
        row = layout.row()
        row.prop(smart_bone_tool, "transform_min", text="min")
        row.prop(smart_bone_tool, "transform_max", text="max")
        
        row = layout.row()
        layout.prop_search(smart_bone_tool, "action_name", bpy.data, "actions")
        row = layout.row()
        row.label(text = 'Frame Range')
        row = layout.row()
        row.prop(smart_bone_tool, "frame_min", text="min")
        row.prop(smart_bone_tool, "frame_max", text="max")
        
        #operator
        
        if (smart_bone_tool.armature_name != "" 
        and smart_bone_tool.control_name != "" 
        and smart_bone_tool.action_name != ""
        and not invalidInput):
            
            layout.row()
            layout.row().label(text = 'Operators')
            layout.operator("myops.add_smart_bone")
            layout.row()
            layout.operator("myops.delete_smart_bone")
            
            layout.separator()
        else:
            layout.row()
            layout.row().label(text = 'Invalid Inputs', icon = "ERROR")

# New Subpanels
class POSE_PT_BendyPanel(bpy.types.Panel):
    bl_label = "Bendy Body Parts"
    bl_idname = "POSE_PT_BendyPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "lattice_resolution")
        layout.prop(tool, "bone_segments")
        layout.prop(tool, "exclude_layers")
        layout.operator("myops.add_bendy_part")

class POSE_PT_ExpressionsPanel(bpy.types.Panel):
    bl_label = "Better Expressions"
    bl_idname = "POSE_PT_ExpressionsPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "expression_type")
        layout.prop(tool, "num_variations")
        layout.prop(tool, "tween_frames")
        layout.operator("myops.add_expression_assets")

class POSE_PT_DepthPanel(bpy.types.Panel):
    bl_label = "Some Depth"
    bl_idname = "POSE_PT_DepthPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "use_depth")
        layout.prop(tool, "depth_offset")
        layout.prop(tool, "parallax_strength")
        layout.operator("myops.add_depth")

class POSE_PT_AutomationPanel(bpy.types.Panel):
    bl_label = "Automation"
    bl_idname = "POSE_PT_AutomationPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "preset_type")
        layout.operator("myops.apply_preset")

class POSE_PT_ColouringPanel(bpy.types.Panel):
    bl_label = "Easier Colouring"
    bl_idname = "POSE_PT_ColouringPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "fill_type")
        layout.operator("myops.add_color")
        for item in tool.color_palette:
            layout.prop(item, "color")
        layout.operator("myops.easy_colour")

class POSE_PT_LayeringPanel(bpy.types.Panel):
    bl_label = "Auto-layering"
    bl_idname = "POSE_PT_LayeringPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.prop(tool, "group_layers")
        layout.prop(tool, "linked_group_name")
        layout.operator("myops.edit_group")

class POSE_PT_AIPanel(bpy.types.Panel):
    bl_label = "AI Tweening (Experimental)"
    bl_idname = "POSE_PT_AIPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Smart Bones"
    bl_parent_id = "POSE_PT_SmartBonePanel"

    def draw(self, context):
        layout = self.layout
        tool = context.scene.smart_bone_tool
        layout.operator("myops.install_ai_deps")
        layout.prop(tool, "interpolator_type")
        if tool.interpolator_type == 'FILM':
            layout.prop(tool, "film_path")
        elif tool.interpolator_type == 'TOONCRAFTER':
            layout.prop(tool, "tooncrafter_path")
            layout.prop(tool, "ai_prompt")
        layout.prop(tool, "model_path")
        layout.prop(tool, "ai_times_to_interpolate")
        layout.operator("myops.ai_tween")

# Menu func for interpolate menu
def interpolate_menu_func(self, context):
    self.layout.separator()
    self.layout.operator(POSE_OT_AITween.bl_idname)

#---------------------------------------------------------------------
#    Register
#---------------------------------------------------------------------

blender_classes = [
    ColorItem,
    SmartBoneProperties,
    POSE_OT_AddSmartBone,
    POSE_OT_DeleteSmartBone,
    POSE_OT_AddBendyPart,
    POSE_OT_AddExpressionAssets,
    POSE_OT_AddDepth,
    POSE_OT_ApplyPreset,
    POSE_OT_AddColor,
    POSE_OT_EasyColour,
    POSE_OT_EditGroup,
    POSE_OT_AITween,
    POSE_OT_InstallAIDeps,
    POSE_PT_SmartBonePanel,
    POSE_PT_BendyPanel,
    POSE_PT_ExpressionsPanel,
    POSE_PT_DepthPanel,
    POSE_PT_AutomationPanel,
    POSE_PT_ColouringPanel,
    POSE_PT_LayeringPanel,
    POSE_PT_AIPanel
]

def register():
    for blender_class in blender_classes:
        bpy.utils.register_class(blender_class)
    
    bpy.types.Scene.smart_bone_tool = bpy.props.PointerProperty(type=SmartBoneProperties)
    bpy.types.GPENCIL_MT_interpolate.append(interpolate_menu_func)
    
def unregister():
    for blender_class in blender_classes:
        bpy.utils.unregister_class(blender_class)

    del bpy.types.Scene.smart_bone_tool
    bpy.types.GPENCIL_MT_interpolate.remove(interpolate_menu_func)


if __name__ == "__main__":
    register()
