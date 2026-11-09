# Renders and 3D model

The scripts behind the renders in `docs/` and the 3D model on
[kyle.au](https://kyle.au/projects/short-temper). Run them from the repo root.

```sh
uv run render/make_meshes.py render/mesh                    # both halves, from case/holster.py
uv run --with pillow python render/make_pcb_texture.py render/mesh
Blender -b -P render/desk.py -- render/mesh render/out 3840 192 hero,controller
uv run render/grade.py render/out render/graded hero,controller
Blender -b -P render/export_glb.py -- render/mesh render/out/short-temper.glb
```

The holster renders use `holster_meshes.py`, `holster_scene.py` and `holster_grade.py` the same way.
`export_glb.py` builds the same scene as `desk.py` and swaps its procedural materials for ones glTF
can carry.
