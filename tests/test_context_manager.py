"""
Testes Unitários para o Gerenciador de Contexto Isolado (ContextManager).
"""

from pathlib import Path
import sys
import unittest

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from context_manager import (
    add_pending_file,
    add_pending_view,
    clear_pending_files,
    clear_pending_views,
    get_current_channel_id,
    get_current_user,
    get_current_user_id,
    get_pending_files,
    get_pending_views,
    set_current_channel_id,
    set_current_user,
    set_current_user_id,
)


class TestContextManager(unittest.TestCase):
    """Valida o isolamento de contexto e armazenamento por usuário."""

    def test_context_vars_basic(self):
        """Testa o armazenamento e recuperação de usuário e canal nas ContextVars."""
        set_current_user("Rodrigo")
        set_current_user_id("123456789")
        set_current_channel_id("987654321")

        self.assertEqual(get_current_user(), "Rodrigo")
        self.assertEqual(get_current_user_id(), "123456789")
        self.assertEqual(get_current_channel_id(), "987654321")

    def test_pending_files_isolation_by_user(self):
        """Testa se arquivos pendentes são isolados por user_id (BUG-08)."""
        # Limpa qualquer estado anterior
        clear_pending_files("user_a")
        clear_pending_files("user_b")

        # Adiciona arquivo para user_a
        set_current_user_id("user_a")
        add_pending_file(Path("/tmp/arquivo_a.pdf"))

        # Adiciona arquivo para user_b
        set_current_user_id("user_b")
        add_pending_file(Path("/tmp/arquivo_b.pdf"))

        # Recupera para user_a e valida isolamento
        arquivos_a = get_pending_files("user_a")
        self.assertEqual(len(arquivos_a), 1)
        self.assertEqual(str(arquivos_a[0]), "/tmp/arquivo_a.pdf")

        # Limpa para user_a e verifica que esvaziou
        clear_pending_files("user_a")
        self.assertEqual(len(get_pending_files("user_a")), 0)

        # Recupera para user_b e valida que não foi afetado pela limpeza do user_a
        arquivos_b = get_pending_files("user_b")
        self.assertEqual(len(arquivos_b), 1)
        self.assertEqual(str(arquivos_b[0]), "/tmp/arquivo_b.pdf")
        clear_pending_files("user_b")

    def test_pending_views_isolation_by_user(self):
        """Testa se views pendentes são isoladas por user_id (BUG-08)."""
        clear_pending_views("user_1")
        clear_pending_views("user_2")

        set_current_user_id("user_1")
        mock_view_1 = {"id": "view_1"}
        add_pending_view(mock_view_1)

        set_current_user_id("user_2")
        mock_view_2 = {"id": "view_2"}
        add_pending_view(mock_view_2)

        views_1 = get_pending_views("user_1")
        self.assertEqual(len(views_1), 1)
        self.assertEqual(views_1[0], mock_view_1)

        views_2 = get_pending_views("user_2")
        self.assertEqual(len(views_2), 1)
        self.assertEqual(views_2[0], mock_view_2)

        clear_pending_views("user_1")
        clear_pending_views("user_2")


if __name__ == "__main__":
    unittest.main()
