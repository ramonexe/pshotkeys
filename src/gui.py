"""
gui.py — PSHotkeys v2 interface.

Telas:
  WizardWindow   — primeiro uso (configuração única do ExtendScript)
  MainWindow     — app principal com sidebar de perfis + lista de atalhos
  BindingEditor  — modal para criar/editar um atalho
  ComboRecorder  — captura combo ao pressionar as teclas
"""

import sys
import threading
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ── Design tokens ─────────────────────────────────────────────────────────────
BG          = "#1a1a1e"
PANEL       = "#222226"
SURFACE     = "#2a2a2f"
SURFACE2    = "#313137"
ACCENT      = "#0d87f5"
ACCENT_DIM  = "#0a6abf"
GREEN       = "#3dba6f"
YELLOW      = "#f5a623"
RED         = "#e5534b"
TEXT        = "#e8e8e8"
TEXT2       = "#888898"
TEXT3       = "#555565"
BORDER      = "#38383f"

F_TITLE  = ("Segoe UI", 13, "bold")
F_HEAD   = ("Segoe UI", 10, "bold")
F_BODY   = ("Segoe UI", 9)
F_MONO   = ("Consolas", 9)
F_SMALL  = ("Segoe UI", 8)


# ── Atalhos nativos do Photoshop ──────────────────────────────────────────────
# Formato: mesmo que ComboRecorder produz (lowercase, keysym tkinter para chars
# especiais: bracketleft, bracketright, comma, period, slash…)

PS_BUILTIN_SHORTCUTS = {
    # Ferramentas (tecla única)
    "v":                        "Mover",
    "a":                        "Seleção Direta / Seta de Componente",
    "m":                        "Seleção Retangular / Elíptica",
    "l":                        "Laço / Laço Poligonal / Laço Magnético",
    "w":                        "Varinha Mágica / Seleção Rápida",
    "c":                        "Cortar",
    "k":                        "Fatia",
    "i":                        "Conta-gotas / Régua / Nota",
    "j":                        "Pincel de Recuperação / Correção",
    "b":                        "Pincel / Lápis / Substituição de Cor",
    "s":                        "Carimbo de Clone / Carimbo de Padrão",
    "y":                        "Pincel de Histórico",
    "e":                        "Borracha / Borracha de Fundo / Borracha Mágica",
    "g":                        "Gradiente / Balde de Tinta",
    "o":                        "Subexpor / Superexpor / Esponja",
    "p":                        "Caneta / Caneta de Forma Livre",
    "t":                        "Texto Horizontal / Vertical",
    "u":                        "Forma (Retângulo, Elipse, etc.)",
    "h":                        "Mão",
    "r":                        "Girar Exibição",
    "z":                        "Zoom",
    "n":                        "Nota",
    "q":                        "Modo de Máscara Rápida",
    "d":                        "Restaurar Cores Padrão (preto/branco)",
    "x":                        "Trocar Cor de Primeiro e Segundo Plano",
    "f":                        "Alternar Modo de Tela",
    # Pincel — tamanho/dureza
    "bracketleft":              "Diminuir Tamanho do Pincel",
    "bracketright":             "Aumentar Tamanho do Pincel",
    # Teclas comuns
    "space":                    "Ferramenta Mão (temporário)",
    "tab":                      "Mostrar/Ocultar Painéis",
    # Ctrl + letra
    "ctrl+a":                   "Selecionar Tudo",
    "ctrl+b":                   "Balanço de Cor",
    "ctrl+c":                   "Copiar",
    "ctrl+d":                   "Desselecionar",
    "ctrl+e":                   "Mesclar Camada Abaixo",
    "ctrl+f":                   "Aplicar Último Filtro",
    "ctrl+g":                   "Agrupar Camadas",
    "ctrl+h":                   "Ocultar Extras (guias, grade, seleção)",
    "ctrl+i":                   "Inverter",
    "ctrl+j":                   "Nova Camada via Cópia",
    "ctrl+k":                   "Preferências",
    "ctrl+l":                   "Níveis",
    "ctrl+m":                   "Curvas",
    "ctrl+n":                   "Novo Documento",
    "ctrl+o":                   "Abrir",
    "ctrl+p":                   "Imprimir",
    "ctrl+q":                   "Sair do Photoshop",
    "ctrl+r":                   "Mostrar/Ocultar Réguas",
    "ctrl+s":                   "Salvar",
    "ctrl+t":                   "Transformação Livre",
    "ctrl+u":                   "Matiz/Saturação",
    "ctrl+v":                   "Colar",
    "ctrl+w":                   "Fechar Documento",
    "ctrl+x":                   "Recortar",
    "ctrl+y":                   "Passo à Frente (Redo)",
    "ctrl+z":                   "Desfazer",
    "ctrl+0":                   "Ajustar à Tela",
    "ctrl+1":                   "Zoom 100%",
    # Ctrl + colchetes (camadas)
    "ctrl+bracketleft":         "Mover Camada Abaixo",
    "ctrl+bracketright":        "Mover Camada Acima",
    # Ctrl + Shift
    "ctrl+shift+a":             "Desselecionar Camadas",
    "ctrl+shift+c":             "Copiar Mesclado",
    "ctrl+shift+e":             "Mesclar Visíveis",
    "ctrl+shift+g":             "Desagrupar Camadas",
    "ctrl+shift+i":             "Inverter Seleção",
    "ctrl+shift+j":             "Nova Camada via Recorte",
    "ctrl+shift+k":             "Configurações de Cor",
    "ctrl+shift+l":             "Auto Tom",
    "ctrl+shift+m":             "Auto Contraste",
    "ctrl+shift+n":             "Nova Camada",
    "ctrl+shift+s":             "Salvar Como",
    "ctrl+shift+u":             "Dessaturar",
    "ctrl+shift+v":             "Colar no Lugar",
    "ctrl+shift+w":             "Fechar Tudo",
    "ctrl+shift+z":             "Refazer (Passo à Frente)",
    "ctrl+shift+bracketleft":   "Enviar Camada para o Fundo",
    "ctrl+shift+bracketright":  "Trazer Camada para a Frente",
    # Ctrl + Alt
    "ctrl+alt+a":               "Selecionar Todas as Camadas",
    "ctrl+alt+c":               "Tamanho da Tela",
    "ctrl+alt+i":               "Tamanho da Imagem",
    "ctrl+alt+r":               "Refinar Borda",
    "ctrl+alt+s":               "Salvar Cópia",
    "ctrl+alt+z":               "Passo Atrás (múltiplos desfazeres)",
    "ctrl+alt+bracketleft":     "Enviar Camada Abaixo",
    "ctrl+alt+bracketright":    "Trazer Camada Acima",
    # Ctrl + Alt + Shift
    "ctrl+alt+shift+e":         "Stamp Visible (Mesclar para Nova Camada)",
    "ctrl+alt+shift+k":         "Atalhos de Teclado",
    "ctrl+alt+shift+m":         "Auto Cor",
    "ctrl+alt+shift+s":         "Salvar para Web",
    # Shift + teclas únicas
    "shift+tab":                "Mostrar/Ocultar Painéis (exceto Ferramentas)",
    # Teclas de função
    "f1":                       "Ajuda do Photoshop",
    "f5":                       "Painel de Pincéis",
    "f6":                       "Painel de Cor",
    "f7":                       "Painel de Camadas",
    "f8":                       "Painel de Informações",
    "f12":                      "Reverter",
    "shift+f5":                 "Preencher",
    "shift+f6":                 "Suavizar Borda",
    "shift+f7":                 "Inverter Seleção",
}


def _btn(parent, text, cmd, bg=SURFACE2, fg=TEXT, bold=False, **kw):
    font = F_HEAD if bold else F_BODY
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  relief="flat", font=font, cursor="hand2",
                  activebackground=SURFACE, activeforeground=TEXT,
                  bd=0, padx=10, pady=5, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=ACCENT_DIM if bg == ACCENT else SURFACE))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b


def _label(parent, text, fg=TEXT, font=F_BODY, **kw):
    bg = kw.pop("bg", parent["bg"])
    # Tk widget config não aceita tuples em pady/padx (só pack/grid aceita)
    for axis in ("pady", "padx"):
        if isinstance(kw.get(axis), tuple):
            kw[axis] = kw[axis][0]
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=font, **kw)


def _entry(parent, **kw):
    return tk.Entry(parent, bg=SURFACE2, fg=TEXT, insertbackground=TEXT,
                    relief="flat", font=F_MONO,
                    highlightbackground=BORDER, highlightthickness=1,
                    **kw)


# ── Combo Recorder ────────────────────────────────────────────────────────────

class ComboRecorder(tk.Toplevel):
    """
    Modal: pressione o combo → exibe → confirme.
    Usa binds do tkinter (cross-platform) + normalização de modificadores.
    """

    _MOD_BITS = {0x4: "ctrl", 0x20000: "alt", 0x1: "shift", 0x8: "win"}

    def __init__(self, parent):
        super().__init__(parent)
        self.result: Optional[str] = None
        self.configure(bg=BG)
        self.title("Gravar Atalho")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()
        self._build()
        self._center(parent)

    def _build(self):
        _label(self, "Pressione o atalho desejado", fg=TEXT2, font=F_BODY,
               pady=18, padx=28).pack()

        self._disp = tk.Label(self, text="—", font=("Consolas", 20, "bold"),
                              bg=SURFACE, fg=ACCENT, width=24, pady=16)
        self._disp.pack(padx=28, fill="x")

        tip = _label(self, "Use Ctrl, Alt, Shift ou teclas simples (ex: , . / q)",
                     fg=TEXT3, font=F_SMALL, pady=6, padx=28)
        tip.pack()

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=28, pady=(8, 20))
        _btn(row, "Cancelar", self.destroy).pack(side="right", padx=(4, 0))
        _btn(row, "Confirmar", self._confirm, bg=ACCENT, fg="white",
             bold=True).pack(side="right")

        self.bind("<KeyPress>", self._press)

    def _press(self, e):
        mods = [v for bit, v in self._MOD_BITS.items() if e.state & bit]
        sym = e.keysym.lower()
        ignore = {"control_l","control_r","alt_l","alt_r","shift_l","shift_r",
                  "super_l","super_r","control","alt","shift"}
        if sym in ignore:
            if mods:
                self._disp.configure(text=" + ".join(m.upper() for m in mods))
            return
        parts = mods + [sym]
        combo = "+".join(parts)
        self.result = combo
        self._disp.configure(text=combo.upper())

    def _confirm(self):
        if self.result:
            self.destroy()
        else:
            messagebox.showwarning("Vazio", "Pressione um atalho primeiro.", parent=self)

    def _center(self, parent):
        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")


# ── Binding Editor ────────────────────────────────────────────────────────────

class BindingEditor(tk.Toplevel):
    """
    Modal para criar ou editar um atalho.

    Tipos de ação disponíveis:
      - Remapear para outro combo
      - Ação especial do PS (lista pré-definida)
      - Código JSX customizado
    """

    PS_ACTIONS = {
        "Rotacionar Canvas ← (15°)":   {"type": "ps_action", "fn": "rotate_canvas_left",  "args": {"step": 15}},
        "Rotacionar Canvas → (15°)":   {"type": "ps_action", "fn": "rotate_canvas_right", "args": {"step": 15}},
        "Rotacionar Canvas ← (5°)":    {"type": "ps_action", "fn": "rotate_canvas_left",  "args": {"step": 5}},
        "Rotacionar Canvas → (5°)":    {"type": "ps_action", "fn": "rotate_canvas_right", "args": {"step": 5}},
        "Resetar Rotação do Canvas":   {"type": "ps_action", "fn": "rotate_canvas_reset", "args": {}},
        "Stamp Visible":               {"type": "ps_action", "fn": "stamp_visible",        "args": {}},
        "Toggle Visibilidade da Camada": {"type": "ps_action", "fn": "toggle_layer_visibility", "args": {}},
        "Flatten para Nova Camada":    {"type": "ps_action", "fn": "flatten_to_new_layer", "args": {}},
    }

    def __init__(self, parent, binding: Optional[dict] = None, engine=None,
                 profile_bindings: Optional[list] = None):
        super().__init__(parent)
        self.result = None
        self._existing = binding or {}
        self._engine = engine
        self._profile_bindings = profile_bindings or []
        self.configure(bg=BG)
        self.title("Editar Atalho" if binding else "Novo Atalho")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._center(parent)
        if binding:
            self._populate(binding)

    def _build(self):
        pad = {"padx": 24, "pady": 6}

        _label(self, "Nome", fg=TEXT2, font=F_SMALL, **pad).pack(fill="x")
        self._name = _entry(self, width=42)
        self._name.pack(fill="x", padx=24, pady=(0, 8))

        # Trigger
        trig_row = tk.Frame(self, bg=BG)
        trig_row.pack(fill="x", padx=24, pady=(0, 8))
        _label(trig_row, "Atalho disparador", fg=TEXT2, font=F_SMALL).pack(anchor="w")
        trig_inner = tk.Frame(trig_row, bg=BG)
        trig_inner.pack(fill="x")
        self._trigger_var = tk.StringVar()
        trig_entry = _entry(trig_inner, textvariable=self._trigger_var, width=28)
        trig_entry.pack(side="left", fill="x", expand=True)
        _btn(trig_inner, "⌨ Gravar", self._record, bg=SURFACE).pack(side="left", padx=(6, 0))

        _label(self, "Tipo de ação", fg=TEXT2, font=F_SMALL, **pad).pack(fill="x")
        self._action_type = tk.StringVar(value="remap")
        types = [("Remapear para outro atalho", "remap"),
                 ("Ação especial do Photoshop", "ps_action"),
                 ("Código JSX customizado", "jsx")]
        for label, val in types:
            tk.Radiobutton(self, text=label, variable=self._action_type,
                           value=val, command=self._on_type_change,
                           bg=BG, fg=TEXT, selectcolor=SURFACE2,
                           activebackground=BG, font=F_BODY).pack(
                anchor="w", padx=28)

        # Frame que muda conforme o tipo
        self._action_frame = tk.Frame(self, bg=BG)
        self._action_frame.pack(fill="x", padx=24, pady=(8, 4))
        self._build_remap_panel()

        # Categoria
        _label(self, "Categoria", fg=TEXT2, font=F_SMALL, **pad).pack(fill="x")
        self._cat = _entry(self, width=22)
        self._cat.insert(0, "Custom")
        self._cat.pack(fill="x", padx=24, pady=(0, 12))

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=24, pady=(0, 20))
        _btn(row, "Cancelar", self.destroy).pack(side="right", padx=(4, 0))
        _btn(row, "Salvar", self._save, bg=ACCENT, fg="white", bold=True).pack(side="right")

    # ── Painéis dinâmicos por tipo ────────────────────────────────────────────

    def _clear_action_frame(self):
        for w in self._action_frame.winfo_children():
            w.destroy()

    def _build_remap_panel(self):
        self._clear_action_frame()
        _label(self._action_frame, "Executar este atalho:", fg=TEXT2, font=F_SMALL).pack(anchor="w")
        inner = tk.Frame(self._action_frame, bg=BG)
        inner.pack(fill="x")
        self._remap_var = tk.StringVar()
        _entry(inner, textvariable=self._remap_var, width=28).pack(side="left", fill="x", expand=True)
        _btn(inner, "⌨ Gravar", self._record_remap, bg=SURFACE).pack(side="left", padx=(6, 0))

    def _build_ps_action_panel(self):
        self._clear_action_frame()
        _label(self._action_frame, "Escolha a ação:", fg=TEXT2, font=F_SMALL).pack(anchor="w")
        self._ps_action_var = tk.StringVar()
        cb = ttk.Combobox(self._action_frame, textvariable=self._ps_action_var,
                          values=list(self.PS_ACTIONS.keys()),
                          state="readonly", font=F_BODY, width=38)
        cb.pack(fill="x", pady=(4, 0))
        if self.PS_ACTIONS:
            cb.set(next(iter(self.PS_ACTIONS)))

    def _build_jsx_panel(self):
        self._clear_action_frame()
        _label(self._action_frame, "Código JSX:", fg=TEXT2, font=F_SMALL).pack(anchor="w")
        self._jsx_text = tk.Text(self._action_frame, bg=SURFACE2, fg=TEXT,
                                 font=F_MONO, height=6, relief="flat",
                                 insertbackground=TEXT)
        self._jsx_text.pack(fill="x", pady=(4, 0))

    def _on_type_change(self):
        t = self._action_type.get()
        if t == "remap":
            self._build_remap_panel()
        elif t == "ps_action":
            self._build_ps_action_panel()
        elif t == "jsx":
            self._build_jsx_panel()

    # ── Gravação de combos ────────────────────────────────────────────────────

    def _record(self):
        if self._engine:
            self._engine.stop()
        rec = ComboRecorder(self)
        self.wait_window(rec)
        if self._engine:
            self._engine.start()
        if rec.result:
            self._trigger_var.set(rec.result)

    def _record_remap(self):
        if self._engine:
            self._engine.stop()
        rec = ComboRecorder(self)
        self.wait_window(rec)
        if self._engine:
            self._engine.start()
        if rec.result:
            self._remap_var.set(rec.result)

    # ── Populate (edição) ─────────────────────────────────────────────────────

    def _populate(self, b: dict):
        self._name.insert(0, b.get("name", ""))
        self._trigger_var.set(b.get("trigger", ""))
        self._cat.delete(0, "end")
        self._cat.insert(0, b.get("category", "Custom"))
        action = b.get("action", {})
        atype = action.get("type", "remap")
        self._action_type.set(atype)
        self._on_type_change()
        if atype == "remap" and hasattr(self, "_remap_var"):
            self._remap_var.set("+".join(action.get("keys", [])))
        elif atype == "ps_action" and hasattr(self, "_ps_action_var"):
            fn = action.get("fn", "")
            for k, v in self.PS_ACTIONS.items():
                if v["fn"] == fn:
                    self._ps_action_var.set(k)
                    break
        elif atype == "jsx" and hasattr(self, "_jsx_text"):
            self._jsx_text.insert("1.0", action.get("code", ""))

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        name = self._name.get().strip()
        trigger = self._trigger_var.get().strip().lower()
        category = self._cat.get().strip() or "Custom"
        atype = self._action_type.get()

        if not name or not trigger:
            messagebox.showwarning("Campos obrigatórios",
                                   "Nome e atalho disparador são obrigatórios.", parent=self)
            return

        # Detecta atalho duplicado no mesmo perfil (exclui o binding sendo editado)
        editing_id = self._existing.get("id")
        for b in self._profile_bindings:
            if b.get("trigger", "").lower() == trigger and b.get("id") != editing_id:
                messagebox.showerror(
                    "Atalho duplicado",
                    f"O atalho  '{trigger.upper()}'  já está em uso por  '{b['name']}'  neste perfil.\n\n"
                    f"Escolha um atalho diferente.",
                    parent=self,
                )
                return

        # Detecta conflito com atalho nativo do Photoshop
        if trigger in PS_BUILTIN_SHORTCUTS:
            ps_desc = PS_BUILTIN_SHORTCUTS[trigger]
            override = messagebox.askyesno(
                "Conflito com atalho do Photoshop",
                f"O atalho  '{trigger.upper()}'  já é usado nativamente pelo Photoshop:\n\n"
                f"      {ps_desc}\n\n"
                f"Se continuar, o PSHotkeys vai interceptar esse atalho e\n"
                f"o Photoshop não o receberá enquanto o PSHotkeys estiver ativo.\n\n"
                f"Deseja sobrepor mesmo assim?",
                parent=self,
                icon="warning",
            )
            if not override:
                return

        action = {}
        if atype == "remap":
            keys = [k.strip() for k in self._remap_var.get().split("+") if k.strip()]
            if not keys:
                messagebox.showwarning("Ação vazia", "Grave o atalho de destino.", parent=self)
                return
            action = {"type": "remap", "keys": keys}
        elif atype == "ps_action":
            sel = self._ps_action_var.get()
            action = self.PS_ACTIONS.get(sel, {})
            if not action:
                messagebox.showwarning("Ação vazia", "Selecione uma ação do Photoshop.", parent=self)
                return
        elif atype == "jsx":
            code = self._jsx_text.get("1.0", "end").strip()
            if not code:
                messagebox.showwarning("JSX vazio", "Escreva o código JSX.", parent=self)
                return
            action = {"type": "jsx", "code": code}

        self.result = {
            "name": name,
            "trigger": trigger,
            "action": action,
            "category": category,
        }
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")


# ── Wizard (primeiro uso) ─────────────────────────────────────────────────────

class WizardWindow(tk.Toplevel):
    """
    Guia o usuário pela configuração única do ExtendScript no PS.
    Aparece apenas no primeiro lançamento.
    """

    STEPS = [
        (
            "Bem-vindo ao PSHotkeys",
            "PSHotkeys permite criar atalhos personalizados que só funcionam\n"
            "quando o Photoshop está aberto — incluindo ações que não existem\n"
            "nativamente, como rotacionar o canvas com uma tecla.",
            None
        ),
        (
            "Configuração única no Photoshop",
            "Para que ações avançadas (rotação de canvas, scripts) funcionem,\n"
            "habilite a comunicação de scripts no Photoshop:",
            "Editar → Preferências → Geral\n→ Marque: \"Permitir que scripts acessem a rede\"\n→ Clique OK e reinicie o Photoshop"
        ),
        (
            "Pronto para usar",
            "O PSHotkeys roda em segundo plano na bandeja do sistema.\n"
            "Enquanto o Photoshop estiver aberto, seus atalhos estarão ativos.\n\n"
            "Use o botão ON/OFF para pausar sem fechar.",
            None
        ),
    ]

    def __init__(self, parent, on_done: Callable):
        super().__init__(parent)
        self.on_done = on_done
        self._step = 0
        self.configure(bg=BG)
        self.title("PSHotkeys — Configuração Inicial")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._render_step()
        self._center(parent)

    def _build(self):
        self._title_lbl = _label(self, "", font=F_TITLE, pady=(24, 4), padx=32)
        self._title_lbl.pack(fill="x")

        self._body_lbl = _label(self, "", fg=TEXT2, font=F_BODY, justify="left",
                                padx=32, pady=8)
        self._body_lbl.pack(fill="x")

        self._code_frame = tk.Frame(self, bg=SURFACE, padx=16, pady=12)
        self._code_lbl = _label(self._code_frame, "", fg=ACCENT, font=F_MONO,
                                justify="left", bg=SURFACE)
        self._code_lbl.pack()

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=32, pady=(16, 28))
        self._back_btn = _btn(btns, "← Voltar", self._back)
        self._back_btn.pack(side="left")
        self._next_btn = _btn(btns, "Próximo →", self._next, bg=ACCENT, fg="white", bold=True)
        self._next_btn.pack(side="right")

    def _render_step(self):
        title, body, code = self.STEPS[self._step]
        self._title_lbl.configure(text=title)
        self._body_lbl.configure(text=body)

        if code:
            self._code_lbl.configure(text=code)
            self._code_frame.pack(fill="x", padx=32, pady=4)
        else:
            self._code_frame.pack_forget()

        is_last = self._step == len(self.STEPS) - 1
        self._next_btn.configure(text="Concluir ✓" if is_last else "Próximo →")
        self._back_btn.configure(state="normal" if self._step > 0 else "disabled")

    def _next(self):
        if self._step < len(self.STEPS) - 1:
            self._step += 1
            self._render_step()
        else:
            self.destroy()
            self.on_done()

    def _back(self):
        if self._step > 0:
            self._step -= 1
            self._render_step()

    def _center(self, parent):
        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow:
    def __init__(self, app_core):
        self.app = app_core
        self.root = tk.Tk()
        self.root.title("PSHotkeys")
        self.root.configure(bg=BG)
        self.root.geometry("700x560")
        self.root.minsize(600, 480)
        self._tray = None

        self._build_ui()
        self._connect_events()
        self._refresh_profiles()
        self._refresh_bindings()
        self._update_status()

        # Primeiro uso?
        if self.app.store.get_setting("wizard_done") is None:
            self.root.after(300, self._show_wizard)

    def _build_ui(self):
        # Remove chrome nativo do Windows
        self.root.overrideredirect(True)
        self._center_on_screen()
        self.root.after(100, self._make_taskbar_visible)

        # ── Borda 1 px ────────────────────────────────────────────────────────
        outer = tk.Frame(self.root, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill="both", expand=True)

        # ── Title bar customizada ─────────────────────────────────────────────
        tb = tk.Frame(inner, bg=PANEL)
        tb.pack(fill="x")
        tb.bind("<ButtonPress-1>", self._drag_start)
        tb.bind("<B1-Motion>",     self._drag_motion)

        # App name (clicável para arrastar)
        app_lbl = tk.Label(tb, text="PS Hotkeys", font=F_TITLE,
                           bg=PANEL, fg=TEXT, padx=16, pady=11, cursor="fleur")
        app_lbl.pack(side="left")
        app_lbl.bind("<ButtonPress-1>", self._drag_start)
        app_lbl.bind("<B1-Motion>",     self._drag_motion)

        # Controles da janela (direita)
        ctrl = tk.Frame(tb, bg=PANEL)
        ctrl.pack(side="right")

        def _wbtn(parent, txt, cmd, hover=SURFACE2, hover_fg=TEXT):
            b = tk.Button(parent, text=txt, command=cmd, bg=PANEL, fg=TEXT2,
                          relief="flat", font=("Segoe UI", 9), cursor="hand2",
                          padx=14, pady=10, bd=0, activeforeground=hover_fg)
            b.bind("<Enter>", lambda e: b.configure(bg=hover, fg=hover_fg))
            b.bind("<Leave>", lambda e: b.configure(bg=PANEL, fg=TEXT2))
            return b

        _wbtn(ctrl, "✕", self._on_close, hover=RED, hover_fg="white").pack(side="right")
        _wbtn(ctrl, "─", self._win_minimize).pack(side="right")

        # Status + toggle (entre o nome e os controles)
        mid = tk.Frame(tb, bg=PANEL)
        mid.pack(side="right", padx=(0, 6))

        self._toggle_btn = tk.Button(
            mid, text=" ON ", font=("Segoe UI", 8, "bold"),
            bg=GREEN, fg="white", relief="flat", cursor="hand2",
            padx=8, pady=3, bd=0, command=self._toggle_master,
            activebackground=GREEN, activeforeground="white",
        )
        self._toggle_btn.pack(side="right", padx=(8, 0))

        self._status_dot = tk.Label(mid, text="●", fg=TEXT3, bg=PANEL, font=("Segoe UI", 9))
        self._status_dot.pack(side="right")
        self._status_lbl = tk.Label(mid, text="Aguardando PS…", fg=TEXT2,
                                    bg=PANEL, font=F_SMALL)
        self._status_lbl.pack(side="right", padx=(0, 4))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")

        # ── Body: sidebar + main ──────────────────────────────────────────────
        body = tk.Frame(inner, bg=BG)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=PANEL, width=168)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="PERFIS", fg=TEXT3, bg=PANEL, font=F_SMALL,
                 anchor="w", padx=14, pady=0).pack(fill="x", pady=(14, 4))

        self._profile_frame = tk.Frame(sidebar, bg=PANEL)
        self._profile_frame.pack(fill="x")

        sidebar_btns = tk.Frame(sidebar, bg=PANEL)
        sidebar_btns.pack(side="bottom", fill="x", pady=8, padx=10)

        self._startup_var = tk.BooleanVar(value=self.app.is_run_at_startup())
        tk.Checkbutton(
            sidebar_btns, text="Iniciar com Windows",
            variable=self._startup_var, command=self._toggle_startup,
            bg=PANEL, fg=TEXT2, selectcolor=SURFACE2,
            activebackground=PANEL, activeforeground=TEXT,
            font=F_SMALL, cursor="hand2",
        ).pack(fill="x", pady=(0, 6))

        _btn(sidebar_btns, "+ Perfil",  self._new_profile,    bg=SURFACE).pack(fill="x", pady=2)
        _btn(sidebar_btns, "Exportar",  self._export_profile, bg=SURFACE).pack(fill="x", pady=2)
        _btn(sidebar_btns, "Importar",  self._import_profile, bg=SURFACE).pack(fill="x", pady=2)

        # Separador vertical
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Área principal
        main = tk.Frame(body, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        toolbar = tk.Frame(main, bg=BG, pady=8, padx=12)
        toolbar.pack(fill="x")
        _btn(toolbar, "+ Novo Atalho", self._new_binding, bg=ACCENT, fg="white",
             bold=True).pack(side="left")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_bindings())
        se = _entry(toolbar, textvariable=self._search_var, width=20)
        se.pack(side="right")
        tk.Label(toolbar, text="🔍", bg=BG, fg=TEXT2).pack(side="right", padx=(0, 4))

        tk.Frame(main, bg=BORDER, height=1).pack(fill="x", padx=12)

        # Lista com scroll
        list_wrap = tk.Frame(main, bg=BG)
        list_wrap.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(list_wrap, bg=BG, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(list_wrap, orient="vertical", command=self._canvas.yview)
        self._list_inner = tk.Frame(self._canvas, bg=BG)

        self._list_inner.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Status bar + grip de redimensionar ───────────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", side="bottom")
        statusbar = tk.Frame(inner, bg=PANEL, pady=4)
        statusbar.pack(fill="x", side="bottom")

        self._log_var = tk.StringVar(value="Pronto.")
        tk.Label(statusbar, textvariable=self._log_var, bg=PANEL, fg=TEXT2,
                 font=F_SMALL, anchor="w", padx=12).pack(side="left", fill="x", expand=True)

        grip = tk.Label(statusbar, text="◢", bg=PANEL, fg=TEXT3,
                        font=("Segoe UI", 8), cursor="size_nw_se", padx=6)
        grip.pack(side="right")
        grip.bind("<ButtonPress-1>", self._resize_start)
        grip.bind("<B1-Motion>",     self._resize_motion)

    # ── Perfis ────────────────────────────────────────────────────────────────

    def _refresh_profiles(self):
        for w in self._profile_frame.winfo_children():
            w.destroy()
        active = self.app.store.active_name()
        for name in self.app.store.profile_names():
            is_active = name == active
            item = tk.Frame(self._profile_frame,
                            bg=SURFACE if is_active else PANEL)
            item.pack(fill="x")
            # Barra lateral colorida para perfil ativo
            tk.Frame(item, bg=ACCENT if is_active else PANEL, width=3).pack(
                side="left", fill="y")
            btn = tk.Button(
                item, text=name,
                bg=SURFACE if is_active else PANEL,
                fg=TEXT if is_active else TEXT2,
                relief="flat", font=F_BODY, cursor="hand2",
                anchor="w", padx=12, pady=7,
                activebackground=SURFACE2, activeforeground=TEXT,
                command=lambda n=name: self._switch_profile(n),
            )
            btn.pack(fill="x", side="left", expand=True)
            item.bind("<Button-3>", lambda e, n=name: self._profile_context(e, n))
            btn.bind("<Button-3>",  lambda e, n=name: self._profile_context(e, n))

    def _switch_profile(self, name: str):
        self.app.switch_profile(name)
        self._refresh_profiles()
        self._refresh_bindings()
        self._log_var.set(f"Perfil: {name}")

    def _new_profile(self):
        name = simpledialog_askstring("Novo Perfil", "Nome do perfil:", parent=self.root)
        if name:
            self.app.create_profile(name.strip())
            self._refresh_profiles()

    def _profile_context(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0, bg=SURFACE2, fg=TEXT, relief="flat")
        menu.add_command(label="Renomear", command=lambda: self._rename_profile(name))
        menu.add_command(label="Exportar", command=lambda: self._export_profile(name))
        menu.add_separator()
        menu.add_command(label="Apagar", foreground=RED,
                         command=lambda: self._delete_profile(name))
        menu.tk_popup(event.x_root, event.y_root)

    def _rename_profile(self, old: str):
        new = simpledialog_askstring("Renomear", f"Novo nome para '{old}':", parent=self.root)
        if new:
            self.app.store.rename_profile(old, new.strip())
            self._refresh_profiles()

    def _delete_profile(self, name: str):
        if messagebox.askyesno("Apagar Perfil", f"Apagar perfil '{name}'?", parent=self.root):
            self.app.delete_profile(name)
            self._refresh_profiles()
            self._refresh_bindings()

    def _export_profile(self, name: Optional[str] = None):
        name = name or self.app.store.active_name()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"{name}.json",
            parent=self.root
        )
        if path:
            ok = self.app.store.export_profile(name, path)
            self._log_var.set(f"Exportado: {path}" if ok else "Erro ao exportar.")

    def _import_profile(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")], parent=self.root)
        if path:
            name = self.app.store.import_profile(path)
            if name:
                self._refresh_profiles()
                self._log_var.set(f"Perfil importado: {name}")
            else:
                messagebox.showerror("Erro", "Arquivo inválido.", parent=self.root)

    # ── Bindings ──────────────────────────────────────────────────────────────

    def _refresh_bindings(self):
        for w in self._list_inner.winfo_children():
            w.destroy()

        profile = self.app.store.active_profile()
        if not profile:
            _label(self._list_inner, "Nenhum perfil ativo.", fg=TEXT3,
                   pady=32).pack()
            return

        q = self._search_var.get().lower()
        bindings = [b for b in profile.get("bindings", [])
                    if not q or q in b["name"].lower() or q in b["trigger"]]

        if not bindings:
            _label(self._list_inner, "Nenhum atalho encontrado.", fg=TEXT3,
                   pady=32).pack()
            return

        cats = {}
        for b in bindings:
            cats.setdefault(b.get("category", "Custom"), []).append(b)

        for cat, items in cats.items():
            _label(self._list_inner, cat.upper(), fg=TEXT3, font=F_SMALL,
                   pady=(10, 2), padx=4).pack(fill="x")
            for b in items:
                self._build_binding_row(b)

    def _build_binding_row(self, b: dict):
        enabled = b.get("enabled", True)
        trigger_key = b["trigger"].lower()
        ps_conflict = trigger_key in PS_BUILTIN_SHORTCUTS

        row = tk.Frame(self._list_inner, bg=SURFACE, pady=0, padx=0)
        row.pack(fill="x", pady=1)

        # Barra lateral colorida
        bar_color = ACCENT if enabled else TEXT3
        tk.Frame(row, bg=bar_color, width=3).pack(side="left", fill="y")

        # Conteúdo
        content = tk.Frame(row, bg=SURFACE, padx=12, pady=10)
        content.pack(side="left", fill="x", expand=True)

        # Linha do nome
        tk.Label(content, text=b["name"], font=F_HEAD, bg=SURFACE,
                 fg=TEXT if enabled else TEXT3, anchor="w").pack(fill="x")

        # Linha de detalhes: badge do trigger + descrição da ação
        detail_row = tk.Frame(content, bg=SURFACE)
        detail_row.pack(fill="x", pady=(3, 0))

        if ps_conflict and enabled:
            badge_bg, badge_fg = YELLOW, BG
            trigger_txt = "⚠ " + b["trigger"].upper()
        elif enabled:
            badge_bg, badge_fg = SURFACE2, ACCENT
            trigger_txt = b["trigger"].upper()
        else:
            badge_bg, badge_fg = SURFACE2, TEXT3
            trigger_txt = b["trigger"].upper()

        tk.Label(detail_row, text=trigger_txt, bg=badge_bg, fg=badge_fg,
                 font=F_MONO, padx=6, pady=1).pack(side="left")

        action = b.get("action", {})
        atype = action.get("type", "remap")
        _fn_labels = {
            "rotate_canvas_left":       "Girar Canvas ←",
            "rotate_canvas_right":      "Girar Canvas →",
            "rotate_canvas_reset":      "Resetar Rotação",
            "stamp_visible":            "Stamp Visible",
            "toggle_layer_visibility":  "Toggle Visibilidade",
            "flatten_to_new_layer":     "Flatten para Camada",
        }
        if atype == "remap":
            action_str = "→ " + "+".join(action.get("keys", [])).upper()
        elif atype == "ps_action":
            action_str = "⚙ " + _fn_labels.get(action.get("fn", ""), action.get("fn", ""))
        elif atype == "jsx":
            action_str = "{ } JSX personalizado"
        else:
            action_str = atype

        tk.Label(detail_row, text=f"  {action_str}",
                 fg=TEXT2 if enabled else TEXT3, bg=SURFACE,
                 font=F_BODY).pack(side="left")

        # Botões de ação
        btn_frame = tk.Frame(row, bg=SURFACE, padx=8)
        btn_frame.pack(side="right", fill="y")

        sid = b["id"]

        def _ibtn(parent, txt, cmd, h_fg=TEXT):
            bw = tk.Button(parent, text=txt, command=cmd, bg=SURFACE, fg=TEXT3,
                           relief="flat", font=F_BODY, cursor="hand2",
                           padx=6, pady=4, bd=0, activeforeground=h_fg)
            bw.bind("<Enter>", lambda e: bw.configure(fg=h_fg))
            bw.bind("<Leave>", lambda e: bw.configure(fg=TEXT3))
            return bw

        _ibtn(btn_frame, "✎", lambda i=sid: self._edit_binding(i),   TEXT2).pack(side="left")
        _ibtn(btn_frame, "⏸" if enabled else "▶",
              lambda i=sid: self._toggle_binding(i), YELLOW).pack(side="left")
        _ibtn(btn_frame, "✕", lambda i=sid: self._delete_binding(i), RED).pack(side="left")

        row.bind("<Enter>", lambda e: row.configure(bg=SURFACE2))
        row.bind("<Leave>", lambda e: row.configure(bg=SURFACE))

    def _new_binding(self):
        self.app.engine.stop()
        profile = self.app.store.active_profile()
        existing = profile.get("bindings", []) if profile else []
        dlg = BindingEditor(self.root, engine=None, profile_bindings=existing)
        self.root.wait_window(dlg)
        self.app.engine.start()
        if dlg.result:
            d = dlg.result
            self.app.add_binding(d["name"], d["trigger"], d["action"], d["category"])
            self._refresh_bindings()

    def _edit_binding(self, bid: str):
        profile = self.app.store.active_profile()
        b = next((x for x in profile.get("bindings", []) if x["id"] == bid), None)
        if not b:
            return
        self.app.engine.stop()
        dlg = BindingEditor(self.root, b, engine=None,
                            profile_bindings=profile.get("bindings", []))
        self.root.wait_window(dlg)
        self.app.engine.start()
        if dlg.result:
            d = dlg.result
            self.app.update_binding(bid, **d)
            self._refresh_bindings()

    def _delete_binding(self, bid: str):
        if messagebox.askyesno("Apagar", "Apagar este atalho?", parent=self.root):
            self.app.delete_binding(bid)
            self._refresh_bindings()

    def _toggle_binding(self, bid: str):
        self.app.toggle_binding(bid)
        self._refresh_bindings()

    # ── Status / ON-OFF ───────────────────────────────────────────────────────

    def _toggle_master(self):
        new_state = not self.app.master_enabled
        self.app.set_master_enabled(new_state)
        self._update_toggle_btn()

    def _update_toggle_btn(self):
        if self.app.master_enabled:
            self._toggle_btn.configure(text="  ON  ", bg=GREEN)
        else:
            self._toggle_btn.configure(text="  OFF  ", bg=SURFACE2)

    def _update_status(self):
        if not self.app.master_enabled:
            self._status_dot.configure(fg=TEXT3)
            self._status_lbl.configure(text="Desativado", fg=TEXT3)
        elif self.app.is_active:
            self._status_dot.configure(fg=GREEN)
            self._status_lbl.configure(text="Photoshop ativo", fg=GREEN)
        else:
            self._status_dot.configure(fg=TEXT3)
            self._status_lbl.configure(text="Aguardando PS…", fg=TEXT3)

    def _connect_events(self):
        self.app.on_status_change(lambda: self.root.after(0, self._update_status))
        self.app.on_shortcut_fired(
            lambda name: self.root.after(0, lambda: self._log_var.set(f"▶ {name}")))

    # ── Wizard ────────────────────────────────────────────────────────────────

    def _show_wizard(self):
        def done():
            self.app.store.set_setting("wizard_done", True)
        WizardWindow(self.root, on_done=done)

    # ── Janela customizada (drag, resize, minimize) ───────────────────────────

    def _center_on_screen(self):
        w, h = 700, 560
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _make_taskbar_visible(self):
        """Força aparição na barra de tarefas mesmo com overrideredirect(True)."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            GWL_EXSTYLE      = -20
            WS_EX_APPWINDOW  = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), 2)
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.root.withdraw()
            self.root.deiconify()
        except Exception:
            pass

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _win_minimize(self):
        self.root.withdraw()

    def _resize_start(self, e):
        self._rsz_x = e.x_root
        self._rsz_y = e.y_root
        self._rsz_w = self.root.winfo_width()
        self._rsz_h = self.root.winfo_height()

    def _resize_motion(self, e):
        w = max(600, self._rsz_w + (e.x_root - self._rsz_x))
        h = max(480, self._rsz_h + (e.y_root - self._rsz_y))
        self.root.geometry(f"{w}x{h}")

    # ── Tray / startup ────────────────────────────────────────────────────────

    def set_tray(self, tray):
        self._tray = tray

    def show(self):
        """Traz a janela ao foco (chamável de qualquer thread via root.after)."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit(self):
        """Encerra completamente o app."""
        self.app.stop()
        if self._tray:
            self._tray.stop()
        self.root.destroy()

    def _toggle_startup(self):
        enabled = self._startup_var.get()
        ok = self.app.set_run_at_startup(enabled)
        if not ok:
            self._startup_var.set(not enabled)
            messagebox.showwarning(
                "Erro", "Não foi possível alterar o registro de startup.",
                parent=self.root)
        else:
            estado = "ativado" if enabled else "desativado"
            self._log_var.set(f"Iniciar com Windows: {estado}")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self._tray and self._tray.available:
            self.root.withdraw()  # Minimiza para tray, não fecha
        else:
            self.quit()


def simpledialog_askstring(title: str, prompt: str, parent=None) -> Optional[str]:
    """Wrapper simples para pedir string (evita import circular)."""
    from tkinter import simpledialog
    return simpledialog.askstring(title, prompt, parent=parent)
