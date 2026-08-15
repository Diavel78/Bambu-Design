#!/usr/bin/env python3
"""
Minimal 3MF writer -- enough of the core spec for Bambu Studio to open.

A .3mf is just a zip holding an XML mesh file. Writing it ourselves means the
bins can be handed over already positioned on the build plate, so opening the
file and pressing Slice is the whole workflow.

One <object> is emitted per unique mesh; identical bins are re-used as extra
<item> entries with their own translation, which keeps the file small.
"""

import zipfile

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def _mesh_xml(mesh, obj_id, name):
    """One <object> element from a trimesh."""
    out = [f'  <object id="{obj_id}" type="model" name="{name}">\n   <mesh>\n'
           '    <vertices>\n']
    for x, y, z in mesh.vertices:
        out.append(f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>\n')
    out.append('    </vertices>\n    <triangles>\n')
    for a, b, c in mesh.faces:
        out.append(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n')
    out.append('    </triangles>\n   </mesh>\n  </object>\n')
    return "".join(out)


def write_3mf(path, meshes, placements, title="drawer bins"):
    """Write a .3mf.

    meshes     -- {key: trimesh.Trimesh}, each centred on its own origin
    placements -- [(key, x_mm, y_mm), ...] bed positions for the mesh centres
    """
    keys = list(meshes)
    ids = {k: i + 1 for i, k in enumerate(keys)}

    doc = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           f'<model unit="millimeter" xml:lang="en-US" xmlns="{NS}">\n',
           f' <metadata name="Title">{title}</metadata>\n',
           ' <metadata name="Application">generate_drawer_boxes.py</metadata>\n',
           ' <resources>\n']
    for k in keys:
        doc.append(_mesh_xml(meshes[k], ids[k], str(k)))
    doc.append(' </resources>\n <build>\n')
    for k, x, y in placements:
        # 3MF transform is a row-major 4x3 matrix; the last row is translation.
        doc.append(f'  <item objectid="{ids[k]}" '
                   f'transform="1 0 0 0 1 0 0 0 1 {x:.4f} {y:.4f} 0"/>\n')
    doc.append(' </build>\n</model>\n')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", "".join(doc))
