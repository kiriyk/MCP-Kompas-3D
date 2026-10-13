# Native 3D workflow, verified KOMPAS v21

Use current tools/list. v0.8 has 80 commands. Model dimensions, origins and volume are mm/mm³; density is g/cm³ (PLA=1.24). Scoped references are strings, not native numeric IDs, and become invalid after Close/Open or server restart.

## Creation and exact plane mapping

connect → create_part(name) returns document_id → create_sketch(document_id,plane,name,offset) returns sketch_reference → sketch_polygon(points) or sketch_circle(x,y,radius) → extrude(depth,operation,reverse,name) returns feature_reference,depth_mm,volume_mm3. Read model_state for bounds_mm, body_count and features. rebuild_model rejects invalid features. save_model accepts .m3d for parts and .a3d for assemblies. close_model closes without saving.

Local sketch coordinates (u,v) map to world coordinates:

| Plane | Point with signed offset h | Positive normal |
|---|---|---|
| XY | (u,v,h) | +Z |
| XZ | (u,h,-v) | +Y |
| YZ | (-h,-v,-u) | -X |

Offset follows the normal. reverse=False extrudes along positive normal for base, boss AND cut; reverse=True goes the other way. Polygon input is one simple closed contour without repeating the first point. Multiple disjoint profiles can use separate sketches/features. Base builds a solid; boss adds material; cut removes it. Extrusion returns an error if the volume did not change in the requested direction. Saved base may appear as kind=boss in native feature tree. Sketch editing is closed even after failures.

Example: box X=[0,20], Y=[10,50], Z=[0,30]: create_sketch(plane="XZ",offset=10), sketch_polygon(points=[[0,0],[20,0],[20,-30],[0,-30]]), extrude(depth=40,operation="base",reverse=False). Expected size=[20,40,30], volume=24000. set_extrusion_depth uses feature_reference; read depth and volume after rebuild. For a reopened feature obtain its fresh reference from model_state.

set_model_color uses integer Windows COLORREF 0x00BBGGRR; transparency=0 opaque. set_model_material(name,density_g_cm3) reads back values. Neither provides a library material selection UI.

## Assemblies

create_assembly → insert_component(path to saved .m3d,name) returns component_reference. set_component_placement(origin,x_axis,y_axis) requires unit perpendicular axes; right-handed Z=cross(X,Y). Every vector is world based. list_components reads placements and file links. Save/reopen and verify them. Assembly bounds and volume include components, even though the native top-part BodyCollection is empty. File links must remain available. Constraints/mates are not exposed; placements are explicit.

## Drawings from model

Save source first. create_drawing → set_sheet → create_model_view(model_path,projection,name,x,y,scale). front projects XZ, top XY, left YZ, isometric uses a fixed orthonormal matrix. Positions are sheet mm; view geometry and dimension endpoints are real model mm. create_section_view(base_view_number,points=[[x1,y1],[x2,y2]],name,x,y,scale) supports a straight, nonzero cut line in base-view mm. The native cut line and source link are retained. Section views disable UseOcclusion: native optimization otherwise removes internal components before section generation. Do not replace actual CAD geometry with manually traced 2D lines.

Activate ALL drawing views using set_active_view(document_id,view_number). Its associative branch uses API5 ksOpenView; setting IView.Current=True directly can zero the scale. update_model_views rebuilds the DOCUMENT (per-view Update only changes properties and may return false on unchanged views). model_view_state reports persisted links, view scale and projected line/circle bounds; curves beyond line/circle are not included in that diagnostic bound. Dimensions created by linear_dimension are native but use explicit endpoints: update them separately after source geometry changes.

save_document → export_pdf/export_png → reopen CDW → model_view_state. Inspect PNG visually: nonzero object count alone does not prove all components are present or captions do not overlap. Keep headers outside the upper-left secondary stamp and allow native captions above views.

## Export and limits

export_model(format="stl",path ending .stl) requires a saved unchanged model; verifies a fresh STL structure, finite solid extents and model size before replacing destination. STL coordinates use mm but STL carries no unit metadata. STEP is explicitly rejected because its converter is unverified here. 3D PNG is NOT a public verified tool; export_png renders a 2D drawing sheet, including native model views. No claim of supporting the entire KOMPAS SDK: fillets, lofts, mates, edge-associated dimensions, collision simulation and parameter constraints are not yet exposed.

## Reproduction

examples/probe_models_mcp.py --output <empty/new folder> exercises native parts, exports, repeated rotated components and linked view rebuild. examples/build_dice_tower.py then examples/build_dice_tower_drawings.py --output <folder> generate the teaching assembly and nine drawings. Read api-development.md before changing SDK methods. Only one COM client at a time; timeout means unknown outcome, not cancellation.

See [native inspection, appearance and repeatable assemblies](inspection-v08.md).
