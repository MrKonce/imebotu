Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Konce\.gemini\antigravity\scratch\ime_staj_bot"
WshShell.Run "pythonw.exe main.py --listen", 0, False
