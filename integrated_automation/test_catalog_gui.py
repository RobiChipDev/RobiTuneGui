"""Real catalog window tests; no hardware ports."""
import tempfile,tkinter as tk,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from tkinter import ttk
from app import App
from propellers import profile,save_catalog,load_catalog

class CatalogGuiTests(unittest.TestCase):
 def test_select_save_as_copy_and_duplicate(self):
  try:root=tk.Tk()
  except tk.TclError as e:
   if 'display' in str(e).lower():self.skipTest('No GUI display')
   raise
  self.addCleanup(root.destroy)
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);row=profile('1050',3,'Black','00','CCW');save_catalog(base,{row['name']:row})
   app=SimpleNamespace(root=root,busy=False,pending_begin=False,cfg={'folder':temp},propeller_name=tk.StringVar(root,row['name']),propeller_combo=Mock())
   app.set_propellers=lambda entries,selected:App.set_propellers(app,entries,selected)
   with patch('app.workspace_root',return_value=base):App.add_propeller(app)
   root.update()
   win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
   def all_widgets(w):
    return [c for child in w.winfo_children() for c in [child,*all_widgets(child)]]
   widgets=all_widgets(win);tree=next(w for w in widgets if isinstance(w,ttk.Treeview))
   buttons={str(w.cget('text')):w for w in widgets if isinstance(w,ttk.Button)}
   fields=[w for w in widgets if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox)]
   rotation=next(w for w in widgets if isinstance(w,ttk.Combobox))
   self.assertEqual(tuple(rotation.cget('values')),('CW','CCW'))
   tree.selection_set(row['name']);root.update()
   buttons['複製名稱'].invoke();self.assertEqual(root.clipboard_get(),row['name'])
   fields[3].delete(0,'end');fields[3].insert(0,'01')
   buttons['複製名稱'].invoke();self.assertEqual(root.clipboard_get(),'1050_3-Blade_Black_No01_CCW')
   buttons['另存新檔'].invoke();root.update()
   entries=load_catalog(base);self.assertEqual(len(entries),2);self.assertEqual(entries[row['name']],row)
   tree.selection_set(row['name']);root.update()
   with patch('app.messagebox.showerror') as error:
    buttons['另存新檔'].invoke();error.assert_called_once()
   self.assertEqual(load_catalog(base),entries)
