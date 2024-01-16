from stability_sdk import api
from stability_sdk.animation import AnimationArgs, Animator
from tqdm import tqdm
from dotenv import load_dotenv
import os
from PIL import Image
import asyncio
import uuid

load_dotenv()
STABILITY_KEY = os.getenv("STABILITY_KEY")

STABILITY_HOST = "grpc.stability.ai:443"

context = api.Context(STABILITY_HOST, STABILITY_KEY)

async def create_gif(folder_path, output_path, frame_duration):
    filenames = sorted(
        os.path.join(folder_path, fname)
        for fname in os.listdir(folder_path)
        if fname.endswith(('.png', '.jpg'))
    )
    images = [Image.open(filename) for filename in filenames]    
    duration_ms = int(frame_duration * 1000)    
    images[0].save(output_path, save_all=True, append_images=images[1:], duration=duration_ms, loop=0)
    return output_path

async def animate(model, anim_type, prompt, config_name=" ", seed=1, output_name=" "):
    if isinstance(prompt, str):
        prompt = [prompt]
    if len(prompt) == 1:
        animation_prompts = [prompt[0]] * 6
    else:
        animation_prompts = prompt + [""] * (6 - len(prompt))
    uuid_str = str(uuid.uuid4())
    if 'avatar' in anim_type:
        width = 512
        height = 768
        output_name = f"{config_name}{anim_type}.gif"
    elif 'background' in anim_type:
        width = 768
        height = 512
        output_name = f"{config_name}{anim_type}.gif"
    elif 'standard' in anim_type:
        width = 768
        height = 768
    else:
        width = 512
        height = 512
    args = AnimationArgs()
    args.model = model
    args.max_frames = 6
    args.border = "replicate"
    args.width = width
    args.height = height
    args.preset = "photographic"
    args.sampler = "K_heun"
    args.cfg_scale = 14
    args.steps_strength_adj = False
    args.interpolate_prompts = True
    args.locked_seed = False
    args.noise_add_curve = "0:(0.01)"
    args.noise_scale_curve = "0:(0.99)"
    args.strength_curve = "0:(0.99)"
    args.steps_curve = "0:(30)"
    args.diffusion_cadence_curve = "0:(1)"
    args.cadence_interp = "rife"
    args.translation_x = "0:(-3.5)"
    args.translation_z = "0:(-2)"
    args.rotation_y = "0:(1.7)"
    args.zoom = "0:(1)"
    args.animation_mode ="3D render"
    args.seed=int(seed)
    animation_prompts = {
        0: animation_prompts[0],
        1: animation_prompts[1],
        2: animation_prompts[2],
        3: animation_prompts[3],
        4: animation_prompts[4],
        5: animation_prompts[5]
    }
    negative_prompt = ""
    animator = Animator(
        api_context=context,
        animation_prompts=animation_prompts,
        negative_prompt=negative_prompt,
        args=args,
        out_dir=f"/media/{config_name}{anim_type}{uuid_str}"
    )
    await asyncio.to_thread(render_animation, animator, args.max_frames)
    finished_animation_path = await create_gif(animator.out_dir, output_name, 0.15)
    return finished_animation_path

def render_animation(animator: Animator, max_frames):
    for _ in tqdm(animator.render(), total=max_frames):
        pass