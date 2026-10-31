"""Guard for /apply Step 5f: the final PDFs land in a folder per application.

The user asked for every drafted CV and cover letter to sit in its own folder
under cv/, named like the CV they already send out, so what they attach to an
application reads "Jane_Doe_CV.pdf", not "main_acme_data_analyst.pdf". The
sources stay where they compile (cv/main_*, cover_letters/cover_*, next to
cover.cls and its fonts); 5f only copies the checked PDFs. These tests pin the
step, its place after the checks, the naming rule, and the ignore rule that
keeps the copies out of git.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APPLY = REPO / ".claude" / "commands" / "apply.md"
GITIGNORE = REPO / ".gitignore"
HEADING = "### 5f. Copy the final PDFs to the application folder"


def section(heading):
    text = APPLY.read_text(encoding="utf-8")
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[text.index(heading) + len(heading):]
    end = re.search(r"^#{1,%d} " % level, rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


class Step5fCopiesThePdfs(unittest.TestCase):
    def setUp(self):
        self.step = section(HEADING)

    def test_step_runs_after_the_checks_and_cleanup(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertLess(text.index("### 5e. Clean up build artifacts"), text.index(HEADING))
        self.assertLess(text.index(HEADING), text.index("## Step 6: Present Final Output"))

    def test_folder_uses_the_shared_subfolder_rule(self):
        self.assertIn("cv/<company>_<role>/", self.step)
        self.assertIn("Subfolder naming", self.step)

    def test_names_come_from_the_users_own_cv(self):
        self.assertIn("documents/cv/", self.step)
        self.assertIn("_Cover_Letter.pdf", self.step)
        self.assertRegex(self.step, r"(?i)no CV there")

    def test_sources_stay_put_and_copies_overwrite_on_redraft(self):
        self.assertRegex(self.step, r"(?i)copy, not move")
        self.assertRegex(self.step, r"(?i)overwrite")

    def test_files_created_lists_the_folder(self):
        files = section("### Files Created")
        self.assertIn("cv/<company>_<role>/", files)


class CopiesStayOutOfGit(unittest.TestCase):
    def test_gitignore_ignores_application_folders(self):
        rules = [l.strip() for l in GITIGNORE.read_text(encoding="utf-8").splitlines()]
        self.assertIn("cv/*/", rules)


if __name__ == "__main__":
    unittest.main()
