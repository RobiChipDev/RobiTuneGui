"""White desktop theme; all colours and widget chrome are defined here."""
from tkinter import ttk

WHITE='#ffffff'
TEXT='#20252b'
MUTED='#68717d'
BORDER='#e2e6eb'


def apply_theme(root):
    root.configure(background=WHITE)
    root.option_add('*Background',WHITE)
    root.option_add('*Foreground',TEXT)
    root.option_add('*Font',('Microsoft JhengHei UI',9))
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('.',background=WHITE,foreground=TEXT,font=('Microsoft JhengHei UI',9),bordercolor=BORDER,lightcolor=WHITE,darkcolor=WHITE,focuscolor=WHITE)
    style.configure('TFrame',background=WHITE)
    style.configure('TLabel',background=WHITE,foreground=TEXT)
    style.configure('TLabelframe',background=WHITE,borderwidth=1,relief='solid',bordercolor=BORDER,lightcolor=WHITE,darkcolor=WHITE)
    style.configure('TLabelframe.Label',background=WHITE,foreground=TEXT,font=('Microsoft JhengHei UI',9,'bold'))
    style.configure('TButton',background=WHITE,foreground=TEXT,padding=(9,5),borderwidth=1,relief='solid',bordercolor=BORDER,lightcolor=WHITE,darkcolor=WHITE,focuscolor=WHITE)
    style.map('TButton',background=[('pressed','#f1f3f5'),('active','#f8f9fb'),('disabled',WHITE)],foreground=[('disabled','#a4aab2')],bordercolor=[('active','#aab3be')],lightcolor=[('active',WHITE)],darkcolor=[('active',WHITE)])
    style.configure('TCheckbutton',background=WHITE,foreground=MUTED,focuscolor=WHITE,indicatorbackground=WHITE)
    style.map('TCheckbutton',background=[('active',WHITE),('disabled',WHITE)],foreground=[('disabled','#a4aab2')])
    style.configure('TEntry',fieldbackground=WHITE,foreground=TEXT,background=WHITE,bordercolor=BORDER,lightcolor=WHITE,darkcolor=WHITE,padding=4)
    style.map('TEntry',fieldbackground=[('disabled',WHITE)],bordercolor=[('focus','#8a96a5')])
    style.configure('TNotebook',background=WHITE,borderwidth=0)
    style.configure('TNotebook.Tab',background=WHITE,padding=(12,6),bordercolor=BORDER)
    style.map('TNotebook.Tab',background=[('selected',WHITE),('active','#f8f9fb')])
    style.configure('Horizontal.TProgressbar',background='#64748b',troughcolor=WHITE,bordercolor=BORDER,lightcolor='#64748b',darkcolor='#64748b',thickness=5,borderwidth=0)
    style.configure('Treeview',background=WHITE,fieldbackground=WHITE,foreground=TEXT,bordercolor=BORDER,rowheight=25)
    style.configure('Treeview.Heading',background=WHITE,foreground=MUTED,relief='flat',padding=6)
    style.map('Treeview',background=[('selected','#eef2f6')],foreground=[('selected',TEXT)])
    root.option_add('*TCombobox*Listbox.background',WHITE)
    root.option_add('*TCombobox*Listbox.foreground',TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground','#e8f1ff')
    root.option_add('*TCombobox*Listbox.selectForeground',TEXT)
    style.configure('Propeller.TCombobox',fieldbackground=WHITE,background=WHITE,
                    foreground=TEXT,arrowcolor=TEXT,bordercolor=BORDER)
    style.map('Propeller.TCombobox',fieldbackground=[('readonly',WHITE),('disabled',WHITE)],
              background=[('readonly',WHITE),('disabled',WHITE)],
              selectbackground=[('readonly','#e8f1ff')],selectforeground=[('readonly',TEXT)])
    return style
