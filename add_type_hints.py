"""Ajoute type hints UNIQUEMENT dans les signatures de fonctions (version sûre)."""
import ast
import re
from pathlib import Path

class SafeTypeHintAdder(ast.NodeVisitor):
    """Ajoute des type hints seulement aux définitions de fonctions."""

    TYPE_MAPPING = {
        # Noms spécifiques à votre projet
        'markets': 'dict',
        'forex_rates': 'dict',
        'config': 'dict',
        'routes': 'list',
        'transactions': 'list',
        'data': 'dict',
        'params': 'dict',
        'options': 'dict',
        'rotation_state': 'dict',
        'rotation_id': 'str',
        'filepath': 'str',
        'path': 'str',
        'filename': 'str',

        # Patterns généraux
        'capital': 'float',
        'rate': 'float',
        'amount': 'float',
        'price': 'float',
        'profit': 'float',
        'fees': 'float',
        'fee': 'float',
        'spread': 'float',
        'ratio': 'float',
        'percent': 'float',

        'count': 'int',
        'index': 'int',
        'num': 'int',
        'cycle': 'int',
        'phase': 'int',

        'message': 'str',
        'text': 'str',
        'name': 'str',
        'key': 'str',
        'value': 'str',
        'url': 'str',

        'enabled': 'bool',
        'active': 'bool',
        'valid': 'bool',
    }

    def __init__(self):
        self.functions_to_update = []

    def guess_type(self, arg_name: str) -> str:
        """Devine le type basé sur le nom."""
        # Exact match
        if arg_name in self.TYPE_MAPPING:
            return self.TYPE_MAPPING[arg_name]

        # Patterns
        if arg_name.startswith('is_') or arg_name.startswith('has_') or arg_name.startswith('can_'):
            return 'bool'

        if arg_name.endswith('_rate') or arg_name.endswith('_amount') or arg_name.endswith('_price'):
            return 'float'

        if arg_name.endswith('_count') or arg_name.endswith('_index') or arg_name.endswith('_num'):
            return 'int'

        if arg_name.endswith('_id') or arg_name.endswith('_name') or arg_name.endswith('_path'):
            return 'str'

        if arg_name.endswith('_dict') or arg_name.endswith('_config') or arg_name.endswith('_data'):
            return 'dict'

        if arg_name.endswith('_list') or arg_name.endswith('s'):  # Pluriel
            return 'list'

        return None  # Ne pas deviner si incertain

    def visit_FunctionDef(self, node):
        """Visite une fonction."""
        hints_needed = []

        for arg in node.args.args:
            if arg.arg in ('self', 'cls'):
                continue

            if arg.annotation is None:
                type_hint = self.guess_type(arg.arg)
                if type_hint:
                    hints_needed.append((arg.arg, type_hint, arg.lineno, arg.col_offset))

        if hints_needed:
            self.functions_to_update.append({
                'func_name': node.name,
                'line': node.lineno,
                'hints': hints_needed
            })

        self.generic_visit(node)


def add_type_hints_manual(filepath: Path):
    """Affiche les suggestions de type hints pour ajout manuel."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)
        visitor = SafeTypeHintAdder()
        visitor.visit(tree)

        if visitor.functions_to_update:
            return visitor.functions_to_update

        return []

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return []


def main():
    """Génère un rapport des type hints à ajouter."""
    project_root = Path.cwd()
    src_dir = project_root / 'src'

    print("=" * 70)
    print("📝 SUGGESTIONS DE TYPE HINTS")
    print("=" * 70)
    print()
    print("⚠️  CE SCRIPT NE MODIFIE PAS LES FICHIERS")
    print("   Il génère seulement des suggestions à ajouter manuellement")
    print()

    if not src_dir.exists():
        print("❌ Dossier src/ introuvable")
        return

    python_files = list(src_dir.rglob('*.py'))
    python_files = [f for f in python_files if f.name != '__init__.py']

    total_suggestions = 0

    for filepath in sorted(python_files):
        suggestions = add_type_hints_manual(filepath)

        if suggestions:
            relative = filepath.relative_to(project_root)
            print(f"📄 {relative}")

            for func in suggestions:
                print(f"   Fonction: {func['func_name']} (ligne {func['line']})")
                for arg_name, type_hint, _, _ in func['hints']:
                    print(f"      • {arg_name} → {type_hint}")
                    total_suggestions += 1
            print()

    print("=" * 70)
    print(f"📊 Total: {total_suggestions} type hints suggérés")
    print("=" * 70)
    print()
    print("💡 Pour ajouter manuellement :")
    print("   1. Ouvrir le fichier dans VS Code")
    print("   2. Sur la ligne def, changer:")
    print("      def func(capital, rate):")
    print("      en:")
    print("      def func(capital: float, rate: float):")
    print()
    print("   3. Ensuite Ctrl+Shift+2 pour générer la docstring")


if __name__ == '__main__':
    main()
