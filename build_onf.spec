from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


project_root = Path.cwd()
mediapipe_datas = collect_data_files(
    "mediapipe",
    includes=[
        "modules/face_detection/**",
        "modules/face_landmark/**",
        "modules/iris_landmark/**",
    ],
)
mediapipe_binaries = collect_dynamic_libs("mediapipe")
qml_source = project_root / "onf_v2" / "ui_qml" / "qml"

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=mediapipe_binaries,
    datas=mediapipe_datas + [(str(qml_source), "onf_v2/ui_qml/qml")],
    hiddenimports=["mediapipe.python.solutions.face_mesh"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Never bundle a UCRT discovered on PATH from an unrelated tool; use Windows' system copy.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.casefold() != "ucrtbase.dll"]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ONF",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
