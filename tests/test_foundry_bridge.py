import unittest,sys,tempfile,json
from pathlib import Path
from helpers import ROOT
from miw.foundry_view import *
class FakeWindow:
    CREATION={'label','button','edit','table','panel','status'}
    def __init__(self,title,**kw):self.controls={};self.calls=[];self.layout_handler=None
    def __getattr__(self,name):
        def call(*args,**kw):
            self.calls.append((name,args,kw))
            if name in self.CREATION:self.controls[args[0]]=name
        return call
class FoundryBridgeTests(unittest.TestCase):
    def test_uses_actual_upstream_runtime(self):
        enable_runtime();from mosaic_ui.headless import HeadlessUI
        self.assertIsInstance(make_headless(),HeadlessUI)
    def test_all_views_navigate(self):
        ui=make_headless()
        for v in VIEWS:
            ui.apply({'intent':'ACTIVATE','node_id':'nav_'+v});self.assertEqual(ui.state['active_view'],v)
    def test_native_fake_host_binds_controls(self):
        enable_runtime();from mosaic_ui.native_realizer import NativeSemanticUI
        ui=NativeSemanticUI(payload(),layout,width=1200,height=800,window_factory=FakeWindow)
        self.assertEqual(len(ui.window.controls),len(ui.items))
        for v in VIEWS:ui.apply({'intent':'ACTIVATE','node_id':'nav_'+v});self.assertEqual(ui.runtime.state['active_view'],v)
    def test_all_headless_projections(self):self.assertEqual(len(headless_smoke()['projections']),len(VIEWS)*3)
    def test_original_sun_unchanged(self):self.assertEqual(digest(read_bytes(ROOT/'assets/mosaic-sun.png')),SUN_SHA)
    def test_only_bounded_navigation_and_workbench_operations(self):
        p=payload();operations=set(p['application']['declared_operation_ids'])
        self.assertEqual({x for x in operations if not x.startswith('navigate_')},
                         {'workbench_validate','workbench_explain','workbench_bind','workbench_lower','workbench_run',
                          'control_refresh','control_compile','control_diagnose','control_headless'})
        self.assertEqual(p['realization']['forbidden_effects'],['NETWORK','RUNTIME_PACKAGE_ACQUISITION','GOVERNED_APPLICATION_EFFECT'])
    def test_no_browser_or_tk_runtime_selected(self):
        p=payload();self.assertFalse(p['realization']['browser_intermediary']);self.assertFalse(p['realization']['tkinter'])
    def test_layout_stays_in_window(self):
        for w,h in [(1000,720),(1200,800),(1600,1000)]:
            for key,(x,y,rw,rh) in layout(w,h).items():
                self.assertGreaterEqual(x,0);self.assertLessEqual(x+rw,w);self.assertLessEqual(y+rh,h)
    def test_upstream_files_remain_pinned(self):
        for row in read_json(ROOT/'vendor/mosaic/UPSTREAM-PIN.json')['files']:
            self.assertEqual(digest(read_bytes(ROOT/'vendor/mosaic'/row['path'])),row['sha256'])
    def test_foundry_recompile_is_identical(self):
        enable_runtime();from mosaic_ui.foundry import compile_library
        with tempfile.TemporaryDirectory() as d:
            compile_library(ROOT/'foundry/source',Path(d),ROOT/'foundry/source/application.json')
            for name in ('library.py','receipt.json'):self.assertEqual((Path(d)/name).read_bytes(),(ROOT/'foundry/generated'/name).read_bytes())
    def test_nonwindows_no_silent_substitution(self):
        if sys.platform!='win32':
            with self.assertRaises(Refusal):launch()
        else:self.assertEqual(sys.platform,'win32')
