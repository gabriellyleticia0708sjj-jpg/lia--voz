"""LIA 3.0 — interface minimalista, esfera animada, voz e IA local."""
import json
import math
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
from ia_local import MotorIA

BASE = Path(__file__).resolve().parent
DATA = BASE / 'dados'
DATA.mkdir(exist_ok=True)
MEMORY = DATA / 'conversas.json'
CONFIG = DATA / 'config.json'
DEFAULTS = {'backend':'ollama','modelo':'llama3.2:1b','openjarvis_url':'http://127.0.0.1:8000',
            'openjarvis_model':'default','falar':True,'palmas':False,'ativacao_voz':False}
BG='#08050f'; PURPLE='#a855f7'; TEXT='#f4eaff'; MUTED='#a99bb9'; PANEL='#160e24'

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    except (OSError, ValueError): return default

class Lia:
    def __init__(self, root):
        self.root=root; root.title('LIA 3.0'); root.geometry('1050x740'); root.minsize(700,530); root.configure(bg=BG)
        self.history=read_json(MEMORY, [])
        self.config={**DEFAULTS, **read_json(CONFIG,{})}
        self.motor=MotorIA(self.config.copy())
        self.busy=False; self.speaking=False; self.listening=False; self.mode='idle'
        self.sidebar_open=False; self.audio_stop=threading.Event(); self.audio_thread=None
        self.audio_lock=threading.Lock(); self.speech_lock=threading.Lock()
        self.frame=0; self.particles=[(random.random()*6.283,random.uniform(.55,1.13),random.random()*6.283) for _ in range(90)]
        self.build_ui(); self.animate()
        if self.config.get('palmas') or self.config.get('ativacao_voz'):
            self.root.after(500,self.start_audio_monitor)
        self.root.protocol('WM_DELETE_WINDOW',self.close)

    def button(self,parent,text,cmd,bg=PANEL,fg=TEXT):
        return tk.Button(parent,text=text,command=cmd,bg=bg,fg=fg,activebackground='#48246c',
                         activeforeground='white',bd=0,relief='flat',font=('Segoe UI',11),cursor='hand2',padx=13,pady=10)

    def build_ui(self):
        self.top=tk.Frame(self.root,bg=BG,height=66); self.top.pack(fill='x'); self.top.pack_propagate(False)
        self.menu_button=self.button(self.top,'•••',self.toggle_sidebar,bg=BG)
        self.menu_button.pack(side='left',padx=18,pady=9)
        self.center=tk.Frame(self.root,bg=BG); self.center.pack(fill='both',expand=True)
        self.orb=tk.Canvas(self.center,bg=BG,highlightthickness=0,height=345)
        self.orb.pack(fill='x',padx=15,pady=(2,0))
        self.reply=tk.Text(self.center,bg=BG,fg=TEXT,font=('Segoe UI',15),relief='flat',wrap='word',
                           bd=0,highlightthickness=0,height=7,spacing2=5,cursor='arrow')
        self.reply.pack(fill='both',expand=True,padx=100,pady=(0,8))
        self.reply.tag_configure('center',justify='center',spacing1=6,spacing3=6)
        self.set_reply('')
        self.composer_outer=tk.Frame(self.root,bg=BG); self.composer_outer.pack(fill='x',padx=60,pady=(10,34))
        self.composer=tk.Frame(self.composer_outer,bg='#21152f',highlightbackground='#51326c',highlightthickness=1)
        self.composer.pack(fill='x')
        self.entry=tk.Entry(self.composer,bg='#21152f',fg=TEXT,insertbackground=TEXT,relief='flat',bd=0,
                            font=('Segoe UI',13))
        self.entry.pack(side='left',fill='x',expand=True,padx=(20,8),ipady=18)
        self.entry.bind('<Return>',lambda event:self.send())
        self.send_button=self.button(self.composer,'➤',self.send,bg='#6d28d9')
        self.send_button.pack(side='right',padx=7,pady=7)
        self.sidebar=tk.Frame(self.root,bg='#140c20',highlightthickness=1,highlightbackground='#36214e')
        self.sidebar.place_forget()
        self.sidebar.lift()
        self.root.bind('<Escape>',lambda e:self.hide_sidebar())
        self.entry.focus_set()

    def set_reply(self,text):
        self.reply.configure(state='normal'); self.reply.delete('1.0','end')
        self.reply.insert('1.0',text,'center'); self.reply.configure(state='disabled')

    def animate(self):
        if not self.root.winfo_exists(): return
        c=self.orb; c.delete('all')
        w=max(c.winfo_width(),600); h=max(c.winfo_height(),340)
        cx=w/2; cy=h/2; t=self.frame*.025
        intensity={'idle':.18,'listening':.55,'thinking':.75,'speaking':1}.get(self.mode,.2)
        pulse=1+intensity*.05*math.sin(t*3.5)
        # concentric rings and orbital arcs, drawn with translucent-looking purple shades
        for k in range(10,0,-1):
            r=(73+k*9)*pulse
            color=['#12091c','#180b27','#210d34','#2b1043','#351453','#401761','#4a1a70','#5b2187','#702ca3','#8741c2'][10-k]
            c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=color,width=1)
        for j in range(6):
            r=(90+j*12)*pulse
            start=(t*(28+j*6)*(1 if j%2 else -1)+j*57)%360
            c.create_arc(cx-r,cy-r,cx+r,cy+r,start=start,extent=65+j*9,style='arc',outline=('#a855f7' if j%2 else '#69309c'),width=1.5+j%2)
        for idx,(angle,rad,phase) in enumerate(self.particles):
            a=angle+t*(.16+intensity*.32)*(1 if idx%2 else -1)
            rr=rad*(118+11*math.sin(t+phase))*pulse
            x=cx+math.cos(a)*rr; y=cy+math.sin(a)*rr*.88
            size=1.1+(idx%4)*.55+intensity*.5
            c.create_oval(x-size,y-size,x+size,y+size,fill=('#d8b4fe' if idx%5==0 else '#7731b4'),outline='')
        for j in range(7,0,-1):
            r=(26+j*6)*(1+intensity*.08*math.sin(t*5))
            colors=['#7c3aed','#6822bf','#5a1c9f','#4b1786','#3b116e','#2a0d52','#190b30']
            c.create_oval(cx-r,cy-r,cx+r,cy+r,fill=colors[7-j],outline='')
        r=23*(1+intensity*.15*math.sin(t*5))
        c.create_oval(cx-r,cy-r,cx+r,cy+r,fill='#b56aff',outline='#e9d5ff',width=1)
        self.frame+=1
        self.root.after(40,self.animate)

    def toggle_sidebar(self):
        if self.sidebar_open:self.hide_sidebar();return
        self.sidebar_open=True; self.sidebar.place(x=12,y=64,width=310,relheight=.86); self.sidebar.lift()
        for child in self.sidebar.winfo_children():child.destroy()
        tk.Label(self.sidebar,text='LIA  •  MENU',bg='#140c20',fg=PURPLE,font=('Segoe UI',16,'bold')).pack(pady=(19,13))
        self.button(self.sidebar,'＋  Novo chat',self.new_chat).pack(fill='x',padx=15,pady=3)
        self.button(self.sidebar,'◷  Histórico',self.show_history).pack(fill='x',padx=15,pady=3)
        self.button(self.sidebar,'🎙  Ouvir agora',self.listen).pack(fill='x',padx=15,pady=3)
        self.button(self.sidebar,'⚙  Configurações',self.show_settings).pack(fill='x',padx=15,pady=3)
        self.button(self.sidebar,'✕  Fechar menu',self.hide_sidebar).pack(fill='x',padx=15,pady=3)

    def hide_sidebar(self):self.sidebar_open=False;self.sidebar.place_forget()

    def show_history(self):
        self.hide_sidebar()
        window=tk.Toplevel(self.root);window.title('LIA • Histórico');window.geometry('650x520');window.configure(bg=BG)
        text=tk.Text(window,bg=PANEL,fg=TEXT,wrap='word',relief='flat',font=('Segoe UI',11),padx=18,pady=15)
        text.pack(fill='both',expand=True,padx=15,pady=15)
        for item in self.history[-200:]:text.insert('end',f"{item.get('autor','')}: {item.get('texto','')}\n\n")
        text.configure(state='disabled')
        self.button(window,'Apagar histórico',lambda:self.clear_history(window)).pack(pady=(0,12))

    def clear_history(self,window):
        if not messagebox.askyesno('Confirmar','Apagar todas as conversas salvas?',parent=window):return
        self.history=[];MEMORY.unlink(missing_ok=True);window.destroy();self.set_reply('Histórico apagado.')

    def new_chat(self):
        self.hide_sidebar();self.set_reply('');self.entry.delete(0,'end')
        # O histórico salvo continua disponível no menu, mas o próximo diálogo começa sem contexto anterior.
        self.history_context_start=len(self.history)

    def show_settings(self):
        self.hide_sidebar(); win=tk.Toplevel(self.root);win.title('LIA • Configurações');win.geometry('480x550');win.configure(bg=BG)
        pane=tk.Frame(win,bg=BG);pane.pack(fill='both',expand=True,padx=25,pady=18)
        tk.Label(pane,text='Configurações',font=('Segoe UI',19,'bold'),fg=TEXT,bg=BG).pack(anchor='w',pady=(0,14))
        backend=tk.StringVar(value=self.config['backend']); model=tk.StringVar(value=self.config['modelo'])
        url=tk.StringVar(value=self.config['openjarvis_url']); jarvis_model=tk.StringVar(value=self.config['openjarvis_model'])
        speak=tk.BooleanVar(value=self.config['falar']); claps=tk.BooleanVar(value=self.config['palmas'])
        wake=tk.BooleanVar(value=self.config['ativacao_voz'])
        def field(label,var):
            tk.Label(pane,text=label,bg=BG,fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',pady=(8,3))
            tk.Entry(pane,textvariable=var,bg=PANEL,fg=TEXT,insertbackground=TEXT,relief='flat',font=('Segoe UI',11)).pack(fill='x',ipady=7)
        field('Motor: ollama ou openjarvis',backend);field('Modelo Ollama',model)
        field('URL OpenJarvis',url);field('Modelo OpenJarvis',jarvis_model)
        for label,var in [('Falar respostas',speak),('Ativação por duas palmas',claps),('Ativação por voz: “LIA” (Vosk local)',wake)]:
            tk.Checkbutton(pane,text=label,variable=var,bg=BG,fg=TEXT,activebackground=BG,activeforeground=TEXT,
                           selectcolor='#392050',font=('Segoe UI',10)).pack(anchor='w',pady=4)
        def save():
            if backend.get().strip().lower() not in ('ollama','openjarvis'):
                messagebox.showerror('Motor inválido','Use ollama ou openjarvis.',parent=win);return
            self.config.update(backend=backend.get().strip().lower(),modelo=model.get().strip() or 'llama3.2:1b',
                               openjarvis_url=url.get().strip(),openjarvis_model=jarvis_model.get().strip(),
                               falar=speak.get(),palmas=claps.get(),ativacao_voz=wake.get())
            CONFIG.write_text(json.dumps(self.config,ensure_ascii=False,indent=2),encoding='utf-8')
            self.motor=MotorIA(self.config.copy());win.destroy();self.restart_audio_monitor()
        self.button(pane,'Salvar configurações',save,bg='#6d28d9').pack(fill='x',pady=15)

    def record(self,who,msg):
        self.history.append({'autor':who,'texto':msg,'data':datetime.now().isoformat()})
        try:MEMORY.write_text(json.dumps(self.history,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:pass

    def send(self):
        if self.busy:return
        msg=self.entry.get().strip()
        if not msg:return
        self.entry.delete(0,'end')
        start=getattr(self,'history_context_start',0)
        context=list(self.history[start:]);self.record('Você',msg)
        self.busy=True;self.mode='thinking';self.set_reply('LIA está pensando…')
        motor=self.motor
        threading.Thread(target=self.answer_worker,args=(motor,msg,context),daemon=True).start()

    def answer_worker(self,motor,msg,context):
        try:
            if msg.lower().strip() in ('que horas são','que horas sao','hora'):
                answer='Agora são '+datetime.now().strftime('%H:%M')+'.'
            elif msg.lower().strip() in ('qual a data de hoje','que dia é hoje','que dia e hoje'):
                answer='Hoje é '+datetime.now().strftime('%d/%m/%Y')+'.'
            else:answer=motor.responder(msg,context)
        except Exception as exc:answer='Não consegui consultar a IA local. Verifique o Ollama e o modelo nas configurações.\n\n'+str(exc)
        self.root.after(0,lambda:self.finish_answer(answer))

    def finish_answer(self,answer):
        self.record('LIA',answer);self.busy=False;self.set_reply(answer);self.mode='idle'
        if self.config.get('falar') and not answer.startswith('Não consegui'):
            self.speak(answer)

    def speak(self,text):
        def worker():
            with self.speech_lock:
                self.root.after(0,lambda:setattr(self,'mode','speaking'))
                try:
                    import pyttsx3
                    engine=pyttsx3.init();engine.setProperty('rate',175);engine.say(text[:1300]);engine.runAndWait();engine.stop()
                except Exception as exc:self.root.after(0,lambda:self.set_reply('Erro na síntese de voz: '+str(exc)))
                finally:self.root.after(0,lambda:setattr(self,'mode','idle'))
        threading.Thread(target=worker,daemon=True).start()

    def listen(self):
        self.hide_sidebar()
        if self.listening:return
        self.listening=True;self.mode='listening';self.audio_stop.set()
        self.set_reply('Estou ouvindo…')
        threading.Thread(target=self.listen_worker,daemon=True).start()

    def listen_worker(self):
        try:
            # Espera o monitor contínuo liberar o microfone.
            with self.audio_lock:
                import speech_recognition as sr
                rec=sr.Recognizer()
                with sr.Microphone() as mic:
                    rec.adjust_for_ambient_noise(mic,duration=.5)
                    audio=rec.listen(mic,timeout=8,phrase_time_limit=12)
                text=rec.recognize_google(audio,language='pt-BR')
            self.root.after(0,lambda:self.voice_received(text))
        except Exception as exc:
            self.root.after(0,lambda:self.set_reply('Não foi possível reconhecer a voz: '+str(exc)))
        finally:
            self.root.after(0,self.finish_listening)

    def voice_received(self,text):
        self.entry.delete(0,'end');self.entry.insert(0,text);self.send()

    def finish_listening(self):
        self.listening=False
        if not self.busy:self.mode='idle'
        self.restart_audio_monitor()

    def restart_audio_monitor(self):
        self.audio_stop.set()
        if not (self.config.get('palmas') or self.config.get('ativacao_voz')):return
        self.root.after(450,self.start_audio_monitor)

    def start_audio_monitor(self):
        if self.listening or self.audio_lock.locked() or not (self.config.get('palmas') or self.config.get('ativacao_voz')):return
        if self.audio_thread and self.audio_thread.is_alive():
            self.root.after(600,self.start_audio_monitor);return
        self.audio_stop=threading.Event()
        self.audio_thread=threading.Thread(target=self.audio_monitor,args=(self.audio_stop,),daemon=True)
        self.audio_thread.start()

    def audio_monitor(self,stop):
        try:
            import sounddevice as sd
            import numpy as np
            wake_enabled=self.config.get('ativacao_voz')
            if wake_enabled:
                from vosk import Model,KaldiRecognizer
                model_dir=BASE/'modelos'/'vosk-pt'
                if not model_dir.is_dir():
                    self.root.after(0,lambda:self.set_reply('Para ativação por voz local, coloque o modelo Vosk em modelos/vosk-pt. Consulte o README.'))
                    wake_enabled=False
                else:
                    recognizer=KaldiRecognizer(Model(str(model_dir)),16000)
            if not wake_enabled and not self.config.get('palmas'):return
            last_peak=0;peaks=[]
            with self.audio_lock:
                with sd.InputStream(samplerate=16000,channels=1,blocksize=1600,dtype='int16') as stream:
                    while not stop.is_set():
                        block,_=stream.read(1600)
                        raw=block.tobytes();now=time.monotonic()
                        if self.config.get('palmas'):
                            amplitude=float(np.max(np.abs(block.astype(np.float32))))/32768
                            if amplitude>.68 and now-last_peak>.18:
                                peaks=[p for p in peaks if now-p<.9];peaks.append(now);last_peak=now
                                if len(peaks)>=2:
                                    stop.set();self.root.after(0,self.listen);return
                        if wake_enabled and recognizer.AcceptWaveform(raw):
                            result=json.loads(recognizer.Result());words=result.get('text','').lower().split()
                            if 'lia' in words or 'lía' in words:
                                stop.set();self.root.after(0,self.listen);return
        except Exception as exc:
            self.root.after(0,lambda e=str(exc):self.set_reply('Erro no monitor de voz/palmas: '+e))

    def close(self):
        self.audio_stop.set();self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();Lia(root);root.mainloop()
