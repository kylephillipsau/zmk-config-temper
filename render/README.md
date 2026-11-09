# Renders and 3D model

The scripts behind the renders in `docs/` and the 3D model on
[kyle.au](https://kyle.au/projects/short-temper). Run them from the repo root.

```sh
uv run render/make_meshes.py render/mesh                    # both halves, from case/holster.py
uv run --with pillow python render/make_pcb_texture.py render/mesh
Blender -b -P render/desk.py -- render/mesh render/out 3840 192 hero,controller
uv run render/grade.py render/out render/graded hero,controller
Blender -b -P render/export_glb.py -- render/mesh render/out/short-temper.glb
uv run render/holster_meshes.py render/holster-mesh
Blender -b -P render/export_glb.py -- render/holster-mesh render/out/short-temper-holster.glb holster
```

The holster renders use `holster_meshes.py`, `holster_scene.py` and `holster_grade.py` the same way.
`export_glb.py` builds the same scene as `desk.py`, or with `holster` as `holster_scene.py`, and
swaps its procedural materials for ones glTF can carry. Each part is its own mesh, so the viewer can
show it alone, and the holster's parts carry how far they move in the exploded view.
