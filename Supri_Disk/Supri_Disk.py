
import csv
import sqlite3
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from database import Database


class SupriDisk(ttk.Frame):

    def __init__(self, master: tk.Tk, db: Database):
        super().__init__(master)

        self.master = master
        self.db = db

        self.master.title("SupriDesk - Cadastro de Materiais")
        self.master.geometry("1150x650")
        self.master.minsize(950, 550)

        self.pack(fill="both", expand=True, padx=10, pady=10)

        self.criar_interface()
        self.atualizar_tabela()

    # ==========================================
    # INTERFACE
    # ==========================================

    def criar_interface(self):

        titulo = ttk.Label(
            self,
            text="Cadastro de Materiais",
            font=("Arial", 18, "bold")
        )
        titulo.pack(pady=(0, 15))

        # BOTÕES DE CADASTRO

        botoes_cadastro = ttk.Frame(self)
        botoes_cadastro.pack(fill="x", pady=5)

        ttk.Button(
            botoes_cadastro,
            text="Novo",
            command=self.novo
        ).pack(side="left", padx=3)

        ttk.Button(
            botoes_cadastro,
            text="Editar",
            command=self.editar
        ).pack(side="left", padx=3)

        ttk.Button(
            botoes_cadastro,
            text="Excluir",
            command=self.excluir
        ).pack(side="left", padx=3)

        ttk.Button(
            botoes_cadastro,
            text="Atualizar",
            command=self.atualizar_tabela
        ).pack(side="left", padx=3)

        ttk.Button(
            botoes_cadastro,
            text="Exportar CSV",
            command=self.exportar_csv
        ).pack(side="left", padx=3)

        # PESQUISA E FILTROS

        filtros = ttk.LabelFrame(
            self,
            text="Pesquisa e filtros"
        )
        filtros.pack(fill="x", pady=10)

        ttk.Label(
            filtros,
            text="Pesquisar:"
        ).pack(side="left", padx=(10, 5), pady=10)

        self.pesquisa_var = tk.StringVar()

        entrada_pesquisa = ttk.Entry(
            filtros,
            textvariable=self.pesquisa_var,
            width=30
        )
        entrada_pesquisa.pack(side="left", padx=5, pady=10)

        self.pesquisa_var.trace_add(
            "write",
            lambda *_: self.atualizar_tabela()
        )

        ttk.Label(
            filtros,
            text="Status:"
        ).pack(side="left", padx=(15, 5), pady=10)

        self.status_var = tk.StringVar(value="Todos")

        combo_status = ttk.Combobox(
            filtros,
            textvariable=self.status_var,
            values=[
                "Todos",
                "Pendente",
                "Em atendimento",
                "Atendida"
            ],
            state="readonly",
            width=18
        )
        combo_status.pack(side="left", padx=5, pady=10)

        combo_status.bind(
            "<<ComboboxSelected>>",
            lambda _: self.atualizar_tabela()
        )

        ttk.Button(
            filtros,
            text="Limpar filtros",
            command=self.limpar_filtros
        ).pack(side="left", padx=10, pady=10)

        # BOTÕES DE ATENDIMENTO

        botoes_atendimento = ttk.LabelFrame(
            self,
            text="Fluxo de atendimento"
        )
        botoes_atendimento.pack(fill="x", pady=5)

        self.btn_iniciar = ttk.Button(
            botoes_atendimento,
            text="Iniciar atendimento",
            command=self.iniciar_atendimento
        )
        self.btn_iniciar.pack(side="left", padx=5, pady=8)

        self.btn_concluir = ttk.Button(
            botoes_atendimento,
            text="Concluir atendimento",
            command=self.concluir_atendimento
        )
        self.btn_concluir.pack(side="left", padx=5, pady=8)

        self.btn_pendente = ttk.Button(
            botoes_atendimento,
            text="Retornar para pendente",
            command=self.retornar_pendente
        )
        self.btn_pendente.pack(side="left", padx=5, pady=8)

        # TABELA

        frame_tabela = ttk.Frame(self)
        frame_tabela.pack(fill="both", expand=True, pady=10)

        colunas = (
            "id",
            "setor",
            "material",
            "quantidade",
            "prioridade",
            "status",
            "data",
            "hora"
        )

        self.tabela = ttk.Treeview(
            frame_tabela,
            columns=colunas,
            show="headings",
            selectmode="browse"
        )

        self.tabela.heading("id", text="ID")
        self.tabela.heading("setor", text="Setor")
        self.tabela.heading("material", text="Material")
        self.tabela.heading("quantidade", text="Quantidade")
        self.tabela.heading("prioridade", text="Prioridade")
        self.tabela.heading("status", text="Status")
        self.tabela.heading("data", text="Data")
        self.tabela.heading("hora", text="Hora")

        self.tabela.column("id", width=50, anchor="center")
        self.tabela.column("setor", width=140)
        self.tabela.column("material", width=180)
        self.tabela.column("quantidade", width=90, anchor="center")
        self.tabela.column("prioridade", width=100, anchor="center")
        self.tabela.column("status", width=130, anchor="center")
        self.tabela.column("data", width=100, anchor="center")
        self.tabela.column("hora", width=100, anchor="center")

        barra_vertical = ttk.Scrollbar(
            frame_tabela,
            orient="vertical",
            command=self.tabela.yview
        )

        self.tabela.configure(
            yscrollcommand=barra_vertical.set
        )

        self.tabela.pack(
            side="left",
            fill="both",
            expand=True
        )

        barra_vertical.pack(
            side="right",
            fill="y"
        )

        self.tabela.bind(
            "<<TreeviewSelect>>",
            lambda _: self.atualizar_botoes_status()
        )

    # ==========================================
    # ATUALIZAR TABELA
    # ==========================================

    def atualizar_tabela(self):

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        try:
            materiais = self.db.listar()

            pesquisa = self.pesquisa_var.get().strip().casefold()
            status_filtro = self.status_var.get()

            for registro in materiais:

                id_material = registro[0]
                setor = registro[1]
                material = registro[2]
                quantidade = registro[3]
                prioridade = registro[4]
                status = registro[5]
                data_hora = registro[6]

                # FILTRO DE PESQUISA

                if pesquisa:
                    if (
                        pesquisa not in setor.casefold()
                        and pesquisa not in material.casefold()
                    ):
                        continue

                # FILTRO DE STATUS

                if (
                    status_filtro != "Todos"
                    and status != status_filtro
                ):
                    continue

                # SEPARAR DATA E HORA

                if data_hora:
                    partes = data_hora.split(" ")
                    data = partes[0] if len(partes) > 0 else ""
                    hora = partes[1] if len(partes) > 1 else ""
                else:
                    data = ""
                    hora = ""

                self.tabela.insert(
                    "",
                    "end",
                    values=(
                        id_material,
                        setor,
                        material,
                        quantidade,
                        prioridade,
                        status,
                        data,
                        hora
                    )
                )

        except sqlite3.Error as erro:
            messagebox.showerror(
                "Erro",
                f"Não foi possível atualizar a tabela:\n{erro}",
                parent=self
            )

        self.atualizar_botoes_status()

    # ==========================================
    # LIMPAR FILTROS
    # ==========================================

    def limpar_filtros(self):

        self.pesquisa_var.set("")
        self.status_var.set("Todos")

        self.atualizar_tabela()

    # ==========================================
    # EXPORTAR CSV
    # ==========================================

    def exportar_csv(self):

        try:
            materiais = self.db.listar()

            if not materiais:
                messagebox.showwarning(
                    "Exportação",
                    "Não existem materiais cadastrados para exportar.",
                    parent=self
                )
                return

            caminho = filedialog.asksaveasfilename(
                parent=self,
                title="Salvar histórico de materiais",
                defaultextension=".csv",
                filetypes=[
                    ("Arquivo CSV", "*.csv"),
                    ("Todos os arquivos", "*.*")
                ],
                initialfile="historico_materiais.csv"
            )

            if not caminho:
                return

            with open(
                caminho,
                mode="w",
                newline="",
                encoding="utf-8-sig"
            ) as arquivo:

                escritor = csv.writer(
                    arquivo,
                    delimiter=";"
                )

                # CABEÇALHO

                escritor.writerow([
                    "ID",
                    "Setor",
                    "Material",
                    "Quantidade",
                    "Prioridade",
                    "Status",
                    "Data/Hora"
                ])

                # REGISTROS

                for registro in materiais:
                    escritor.writerow(registro)

            messagebox.showinfo(
                "Exportação concluída",
                f"Histórico exportado com sucesso!\n\n"
                f"Arquivo salvo em:\n{caminho}",
                parent=self
            )

        except (sqlite3.Error, OSError, csv.Error) as erro:

            messagebox.showerror(
                "Erro na exportação",
                f"Não foi possível exportar o histórico:\n{erro}",
                parent=self
            )

    # ==========================================
    # SELEÇÃO DE REGISTRO
    # ==========================================

    def obter_id_selecionado(self):

        selecionado = self.tabela.selection()

        if not selecionado:
            messagebox.showwarning(
                "Atenção",
                "Selecione um material na tabela.",
                parent=self
            )
            return None

        valores = self.tabela.item(selecionado[0], "values")

        return int(valores[0])

    # ==========================================
    # ATUALIZAR BOTÕES DE STATUS
    # ==========================================

    def atualizar_botoes_status(self):

        selecionado = self.tabela.selection()

        self.btn_iniciar.config(state="disabled")
        self.btn_concluir.config(state="disabled")
        self.btn_pendente.config(state="disabled")

        if not selecionado:
            return

        valores = self.tabela.item(
            selecionado[0],
            "values"
        )

        status = valores[5]

        if status == "Pendente":
            self.btn_iniciar.config(state="normal")

        elif status == "Em atendimento":
            self.btn_concluir.config(state="normal")
            self.btn_pendente.config(state="normal")

    # ==========================================
    # NOVO MATERIAL
    # ==========================================

    def novo(self):

        FormularioMaterial(
            self,
            titulo="Novo Material",
            callback=self.salvar_novo
        )

    def salvar_novo(self, dados):

        try:
            self.db.inserir(
                dados["setor"],
                dados["material"],
                dados["quantidade"],
                dados["prioridade"]
            )

            self.atualizar_tabela()

            messagebox.showinfo(
                "Sucesso",
                "Material cadastrado com sucesso!",
                parent=self
            )

        except (sqlite3.Error, ValueError) as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    # ==========================================
    # EDITAR MATERIAL
    # ==========================================

    def editar(self):

        id_material = self.obter_id_selecionado()

        if id_material is None:
            return

        try:
            materiais = self.db.listar()

            registro = next(
                (
                    item for item in materiais
                    if item[0] == id_material
                ),
                None
            )

            if registro is None:
                messagebox.showerror(
                    "Erro",
                    "Material não encontrado.",
                    parent=self
                )
                return

            FormularioMaterial(
                self,
                titulo="Editar Material",
                callback=lambda dados: self.salvar_edicao(
                    id_material,
                    dados
                ),
                dados={
                    "setor": registro[1],
                    "material": registro[2],
                    "quantidade": registro[3],
                    "prioridade": registro[4]
                }
            )

        except sqlite3.Error as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    def salvar_edicao(self, id_material, dados):

        try:
            self.db.atualizar(
                id_material,
                dados["setor"],
                dados["material"],
                dados["quantidade"],
                dados["prioridade"]
            )

            self.atualizar_tabela()

            messagebox.showinfo(
                "Sucesso",
                "Material atualizado com sucesso!",
                parent=self
            )

        except (sqlite3.Error, ValueError) as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    # ==========================================
    # EXCLUIR MATERIAL
    # ==========================================

    def excluir(self):

        id_material = self.obter_id_selecionado()

        if id_material is None:
            return

        confirmar = messagebox.askyesno(
            "Confirmar exclusão",
            "Deseja realmente excluir este material?",
            parent=self
        )

        if not confirmar:
            return

        try:
            self.db.excluir(id_material)

            self.atualizar_tabela()

            messagebox.showinfo(
                "Sucesso",
                "Material excluído com sucesso!",
                parent=self
            )

        except sqlite3.Error as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    # ==========================================
    # INICIAR ATENDIMENTO
    # ==========================================

    def iniciar_atendimento(self):

        id_material = self.obter_id_selecionado()

        if id_material is None:
            return

        try:
            self.db.iniciar_atendimento(id_material)

            self.atualizar_tabela()

            messagebox.showinfo(
                "Atendimento",
                "Atendimento iniciado com sucesso!",
                parent=self
            )

        except (sqlite3.Error, ValueError) as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    # ==========================================
    # CONCLUIR ATENDIMENTO
    # ==========================================

    def concluir_atendimento(self):

        id_material = self.obter_id_selecionado()

        if id_material is None:
            return

        try:
            self.db.concluir_atendimento(id_material)

            self.atualizar_tabela()

            messagebox.showinfo(
                "Atendimento",
                "Atendimento concluído com sucesso!",
                parent=self
            )

        except (sqlite3.Error, ValueError) as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )

    # ==========================================
    # RETORNAR PARA PENDENTE
    # ==========================================

    def retornar_pendente(self):

        id_material = self.obter_id_selecionado()

        if id_material is None:
            return

        try:
            self.db.retornar_pendente(id_material)

            self.atualizar_tabela()

            messagebox.showinfo(
                "Atendimento",
                "Material retornado para pendente!",
                parent=self
            )

        except (sqlite3.Error, ValueError) as erro:
            messagebox.showerror(
                "Erro",
                str(erro),
                parent=self
            )


# ==========================================
# FORMULÁRIO DE MATERIAL
# ==========================================

class FormularioMaterial(tk.Toplevel):

    def __init__(
        self,
        master,
        titulo,
        callback,
        dados=None
    ):

        super().__init__(master)

        self.callback = callback

        self.title(titulo)
        self.geometry("400x350")
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        dados = dados or {}

        self.setor_var = tk.StringVar(
            value=dados.get("setor", "")
        )

        self.material_var = tk.StringVar(
            value=dados.get("material", "")
        )

        self.quantidade_var = tk.StringVar(
            value=str(dados.get("quantidade", ""))
        )

        self.prioridade_var = tk.StringVar(
            value=dados.get("prioridade", "Normal")
        )

        self.criar_interface()

    def criar_interface(self):

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        # SETOR

        ttk.Label(
            frame,
            text="Setor:"
        ).pack(anchor="w")

        ttk.Entry(
            frame,
            textvariable=self.setor_var
        ).pack(fill="x", pady=(3, 12))

        # MATERIAL

        ttk.Label(
            frame,
            text="Material:"
        ).pack(anchor="w")

        ttk.Entry(
            frame,
            textvariable=self.material_var
        ).pack(fill="x", pady=(3, 12))

        # QUANTIDADE

        ttk.Label(
            frame,
            text="Quantidade:"
        ).pack(anchor="w")

        ttk.Entry(
            frame,
            textvariable=self.quantidade_var
        ).pack(fill="x", pady=(3, 12))

        # PRIORIDADE

        ttk.Label(
            frame,
            text="Prioridade:"
        ).pack(anchor="w")

        combo_prioridade = ttk.Combobox(
            frame,
            textvariable=self.prioridade_var,
            values=["Normal", "Alta"],
            state="readonly"
        )

        combo_prioridade.pack(
            fill="x",
            pady=(3, 15)
        )

        # BOTÕES

        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", pady=10)

        ttk.Button(
            botoes,
            text="Salvar",
            command=self.salvar
        ).pack(side="left", expand=True, fill="x", padx=3)

        ttk.Button(
            botoes,
            text="Cancelar",
            command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=3)

    def salvar(self):

        setor = self.setor_var.get().strip()
        material = self.material_var.get().strip()
        quantidade_texto = self.quantidade_var.get().strip()
        prioridade = self.prioridade_var.get()

        if not setor:
            messagebox.showwarning(
                "Validação",
                "Informe o setor.",
                parent=self
            )
            return

        if not material:
            messagebox.showwarning(
                "Validação",
                "Informe o material.",
                parent=self
            )
            return

        try:
            quantidade = int(quantidade_texto)

            if quantidade <= 0:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Validação",
                "A quantidade deve ser um número inteiro maior que zero.",
                parent=self
            )
            return

        if prioridade not in ("Normal", "Alta"):
            messagebox.showwarning(
                "Validação",
                "Selecione uma prioridade válida.",
                parent=self
            )
            return

        dados = {
            "setor": setor,
            "material": material,
            "quantidade": quantidade,
            "prioridade": prioridade
        }

        self.callback(dados)
        self.destroy()


# ==========================================
# INICIALIZAÇÃO
# ==========================================

def main():

    caminho_banco = Path(__file__).with_name(
        "solicitacoes.db"
    )

    db = Database(caminho_banco)

    root = tk.Tk()

    estilo = ttk.Style()

    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    app = SupriDisk(root, db)

    def fechar_aplicacao():
        db.fechar()
        root.destroy()

    root.protocol(
        "WM_DELETE_WINDOW",
        fechar_aplicacao
    )

    root.mainloop()


if __name__ == "__main__":
    main()
