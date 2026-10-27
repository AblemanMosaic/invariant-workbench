"""Read-only native Tk reference viewer. No Mosaic UI Foundry binding claimed."""
from __future__ import annotations
from pathlib import Path
import json
from .common import Refusal,read_json,read_bytes
from .dossier import verify_dossier

def make_window(folder:Path):
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError as exc:raise Refusal('TKINTER_UNAVAILABLE') from exc
    checked=verify_dossier(folder)
    summary=read_json(folder/'SUMMARY.json')
    try:window=tk.Tk()
    except tk.TclError as exc:raise Refusal('DESKTOP_DISPLAY_UNAVAILABLE') from exc
    window.title('Mosaic Invariant Workbench | Turn 2 candidate')
    window.geometry('1120x780');window.minsize(850,600)
    window.configure(background='#11161d')
    style=ttk.Style(window);style.theme_use('clam')
    style.configure('TFrame',background='#11161d')
    style.configure('TLabel',background='#11161d',foreground='#edf1f6')
    style.configure('TNotebook',background='#11161d',borderwidth=0)
    style.configure('TNotebook.Tab',padding=(18,10),background='#273140',foreground='#edf1f6')
    style.map('TNotebook.Tab',background=[('selected','#3a4b61')],foreground=[('selected','#ffffff')])
    header=ttk.Frame(window,padding=(24,18));header.pack(fill='x')
    ttk.Label(header,text='MOSAIC  /  INVARIANT WORKBENCH',font=('TkDefaultFont',11)).pack(anchor='w')
    ttk.Label(header,text='Rules. Code. Evidence.',font=('TkDefaultFont',24,'bold')).pack(anchor='w',pady=(4,8))
    ttk.Label(header,text='TURN 2 CANDIDATE  |  INFORMATION ONLY  |  NO RELEASE AUTHORITY').pack(anchor='w')
    ttk.Label(window,text='Local-only reference viewer. Exact artifacts, bounded claims, no network.',padding=(24,8)).pack(side='bottom',fill='x')
    tabs=ttk.Notebook(window);tabs.pack(fill='both',expand=True,padx=24,pady=(0,16))
    def page(title,content):
        frame=ttk.Frame(tabs);tabs.add(frame,text=title)
        text=tk.Text(frame,wrap='word',background='#1b222c',foreground='#edf1f6',insertbackground='white',
                     borderwidth=0,padx=18,pady=16,font=('TkFixedFont',11))
        scroll=ttk.Scrollbar(frame,command=text.yview);scroll.pack(side='right',fill='y')
        text.configure(yscrollcommand=scroll.set);text.pack(fill='both',expand=True)
        text.insert('1.0',content);text.configure(state='disabled')
    overview=['STATIC PROOF RECHECKED AGAINST THE BUNDLED SOURCE SNAPSHOTS','']
    for e in summary['examples']:
        overview.extend([e['name'].upper(),f"  {e['proof_outcome']}",
            f"  {e['native_vc_count']} native verification conditions; {e['path_count']} symbolic path clauses",
            f"  {e['scenario_passes']}/{e['scenario_count']} recorded examples passed",''])
    overview.extend(['BOUNDARIES','The new restricted Python frontend is trusted, not formally proved.',
        'The interpreter, OS and hardware are assumptions. No C++, database or physical-stock proof.',
        'Recorded tests are not rerun merely by opening this viewer.',
        'Zucchini examples are synthetic import fixtures. No upstream build was run.',
        'This reference viewer is not integrated with the Mosaic UI Foundry.'])
    page('Overview','\n'.join(overview))
    page('Rule',json.dumps(read_json(folder/'assembly.contract.json'),indent=2))
    page('Code',read_bytes(folder/'assembly.source.py').decode()+'\n\n'+read_bytes(folder/'assembly.feature').decode())
    page('Evidence',json.dumps({'fresh_proof_rechecks':checked,'mutations':summary['mutations']},indent=2))
    page('Dependencies',json.dumps({'graph':read_json(folder/'graph.json'),'impact':read_json(folder/'impact.json')},indent=2))
    page('Zucchini',json.dumps(read_json(folder/'zucchini.execution-link.json'),indent=2))
    return window

def launch(folder:Path):
    window=make_window(folder);window.mainloop()
