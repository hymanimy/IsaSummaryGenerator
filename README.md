# Isabelle Proof Stripper (`strip_proofs.py`)

This Python script reads an Isabelle/HOL theory file (`.thy`) and creates a summary version. It keeps all definitions, datatypes, and lemma statements, but removes the proofs and replaces them with `sorry`. This allows the summary file to still build in Isabelle.

## Features

* **Removes Proofs:** Identifies and removes both structured proofs (`proof ... qed`) and unstructured apply chains (`apply ... done/by/.`).
* **Maintains Structure:** Replaces removed proofs with a single `sorry` so the theory file remains valid.
* **Syntax Masking:** Hides strings (`"..."`) and Isabelle cartouches (`‹...›` and `\<open>...\<close>`) during processing. This prevents words like `by` or `proof` inside text blocks from breaking the parser.
* **Auto-Renaming:** Automatically updates the `theory OLDNAME` declaration at the top of the file to match the new output filename.

## Usage

Run the script from the command line, providing the input file and the desired output file:

```bash
python strip_proofs.py InputFile.thy OutputFile.thy
```

**Example:**

```bash
python strip_proofs.py Value.thy Value_Summary.thy
```

This will read `Value.thy`, strip the proofs, change the theory name to `Value_Summary`, and save the result as `Value_Summary.thy`.

## Notes

Because Isabelle syntax is complex, this script relies on a state machine and string masking rather than a full syntax tree parser. It works for standard formatting but may require minor manual adjustments if a file has unusual line breaks or proof structures.
