# __init__.py — OFFICIAL RELEASE VERSION
# BlendArmory Muscles 3.3 — The Best Free Muscle System Ever Made

bl_info = {
    "name": "BlendArmory Muscles",
    "author": "Grok + Himadri",
    "version": (3, 3, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Muscles",
    "description": "The most advanced free muscle system — XMuscle shapes, Auto-Rig Pro ready, bendy bones, pinning, micro controllers",
    "doc_url": "https://github.com/Himadri-Tech/Blender-Add-ons",
    "tracker_url": "https://github.com/Himadri-Tech/Blender-Add-ons/issues",
    "support": "COMMUNITY",
    "category": "Rigging",
}

import bpy

# Import modules
from . import data
from . import panel
from . import system
from . import arp_integration


def register():
    data.register()
    system.register()
    panel.register()
    arp_integration.register()

    print("\n" + "═" * 70)
    print(" BLENDARMORY MUSCLES 3.3 — SUCCESSFULLY LOADED")
    print(" • Full XMuscle vertex data (real shapes)")
    print(" • Auto-Rig Pro auto-detection & bone mapping")
    print(" • Bendy bones + volume preservation")
    print(" • Pinning system + micro controllers")
    print(" • Skin shrinkwrap + corrective smooth")
    print(" • Modular, clean, fast, and 100% free")
    print(" • Created by Grok + Himadri")
    print(" • https://github.com/Himadri-Tech/Blender-Add-ons")
    print("═" * 70 + "\n")


def unregister():
    arp_integration.unregister()
    panel.unregister()
    system.unregister()
    data.unregister()


if __name__ == "__main__":
    register()