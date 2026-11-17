"""Select an existing CSV and regenerate a report without opening devices."""
from pathlib import Path
import sys
import webbrowser
from report import generate_report

def main():
    root=None
    if len(sys.argv)>1:
        path=sys.argv[1]
    else:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw()
        path=filedialog.askopenfilename(title='選取實驗原始 data.csv（勿選 summary / stages）',filetypes=[('CSV','*.csv')])
    if not path:
        if root:root.destroy()
        return
    try:
        output=generate_report(Path(path))
        print('報告已保存：',output)
        webbrowser.open(output.resolve().as_uri())
    except Exception as exc:
        if root:
            from tkinter import messagebox
            messagebox.showerror('報告建立失敗',str(exc))
        else:raise
    finally:
        if root:root.destroy()

if __name__=='__main__':main()
