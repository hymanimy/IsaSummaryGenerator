import sys
import os
import re

def strip_isabelle_proofs(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Determine the target theory name from the output filename
    base_name = os.path.basename(output_path)
    theory_name = os.path.splitext(base_name)[0]

    # 1. Strip nested comments (* ... *)
    stripped_content = []
    comment_level = 0
    i = 0
    while i < len(content):
        if content[i:i+2] == "(*":
            comment_level += 1
            i += 2
        elif content[i:i+2] == "*)" and comment_level > 0:
            comment_level -= 1
            i += 2
        elif comment_level == 0:
            stripped_content.append(content[i])
            i += 1
        else:
            i += 1
    
    content = "".join(stripped_content)
    lines = content.splitlines()
    
    # 2. Create a "masked" version of the lines where strings and cartouches are hidden.
    masked_lines = []
    in_string = False
    cartouche_depth = 0
    for line in lines:
        masked_chars = []
        i = 0
        while i < len(line):
            # Mask Isabelle cartouches (\<open> ... \<close> or ‹ ... ›)
            if not in_string and line[i:i+7] == r'\<open>':
                cartouche_depth += 1
                masked_chars.extend([' '] * 7)
                i += 7
            elif not in_string and line[i:i+8] == r'\<close>' and cartouche_depth > 0:
                cartouche_depth -= 1
                masked_chars.extend([' '] * 8)
                i += 8
            elif not in_string and line[i] == '‹':
                cartouche_depth += 1
                masked_chars.append(' ')
                i += 1
            elif not in_string and line[i] == '›' and cartouche_depth > 0:
                cartouche_depth -= 1
                masked_chars.append(' ')
                i += 1
            elif cartouche_depth > 0:
                masked_chars.append(' ')
                i += 1
            # Mask strings
            elif line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_string = not in_string
                masked_chars.append(' ') 
                i += 1
            elif in_string:
                masked_chars.append(' ') 
                i += 1
            else:
                masked_chars.append(line[i])
                i += 1
        masked_lines.append("".join(masked_chars))

    # 3. Strip proofs and replace with sorry
    final_lines = []
    proof_depth = 0
    in_apply_chain = False

    for idx, line in enumerate(lines):
        masked_line = masked_lines[idx]
        stripped_masked = masked_line.strip()
        
        # Keep structurally empty lines unless we are removing a proof
        if not stripped_masked:
            if proof_depth == 0 and not in_apply_chain:
                final_lines.append(line)
            continue

        # Rename the theory to match the new output file
        first_word = stripped_masked.split()[0] if stripped_masked.split() else ""
        if proof_depth == 0 and not in_apply_chain and first_word == "theory":
            new_line = re.sub(r'^(\s*theory\s+)\S+', r'\g<1>' + theory_name, line)
            final_lines.append(new_line)
            continue

        # Robust triggers that catch spaces AND parentheses
        is_proof = stripped_masked == "proof" or stripped_masked.startswith("proof ") or stripped_masked.startswith("proof(")
        is_qed   = stripped_masked == "qed" or stripped_masked.startswith("qed ") or stripped_masked.startswith("qed(")
        is_apply = stripped_masked == "apply" or stripped_masked.startswith("apply ") or stripped_masked.startswith("apply(")
        is_by    = stripped_masked == "by" or stripped_masked.startswith("by ") or stripped_masked.startswith("by(")
        is_done  = stripped_masked == "done"
        is_dot   = stripped_masked == "." or stripped_masked == ".."
        is_sorry = stripped_masked == "sorry" or stripped_masked == "oops"

        # Check for inline terminators (e.g., "using assms by auto")
        inline_by_match = re.search(r'\s+by(\s|\()', masked_line)
        inline_sorry_match = re.search(r'\s+(sorry|oops)(\s|$)', masked_line)
        ends_with_dot = stripped_masked.endswith(" ..") or stripped_masked.endswith(" .")

        # If any of these are true, the current apply chain is officially over
        terminates_apply = is_done or is_by or is_dot or is_sorry or is_qed or inline_by_match or inline_sorry_match or ends_with_dot

        # --- State 1: Inside a structured proof block ---
        if proof_depth > 0:
            if is_proof:
                proof_depth += 1
            elif is_qed:
                proof_depth -= 1
            continue

        # --- State 2: Inside an unstructured apply chain ---
        if in_apply_chain:
            if is_proof:
                proof_depth = 1
                in_apply_chain = False
            elif terminates_apply:
                in_apply_chain = False
            continue

        # --- State 3: OUTSIDE any proof ---
        
        # Start of a structured proof
        if is_proof:
            proof_depth = 1
            final_lines.append("  sorry")
            continue
            
        # Start of an apply chain
        if is_apply:
            in_apply_chain = True
            final_lines.append("  sorry")
            continue
            
        # Standalone single-line proof
        if is_by or is_dot or is_sorry:
            final_lines.append("  sorry")
            continue
            
        # Inline proof on the same line using `by`
        if inline_by_match:
            split_idx = inline_by_match.start()
            final_lines.append(line[:split_idx] + " sorry")
            continue
            
        # Inline sorry or oops
        if inline_sorry_match:
            split_idx = inline_sorry_match.start()
            final_lines.append(line[:split_idx] + " sorry")
            continue

        # Inline dot proof (e.g., `..` or `.`)
        if ends_with_dot:
            if stripped_masked.endswith(" .."):
                idx = masked_line.rfind(" ..")
            else:
                idx = masked_line.rfind(" .")
            final_lines.append(line[:idx] + " sorry")
            continue

        # Keep the original line if no proof triggers hit
        final_lines.append(line)

    # 4. Filter out excessive blank lines
    output = []
    prev_empty = False
    for line in final_lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        output.append(line)
        prev_empty = is_empty

    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write("\n".join(output))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python strip_proofs.py <input_file.thy> <output_file.thy>")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        strip_isabelle_proofs(input_file, output_file)
        print(f"Processed {input_file}. Stripped output saved to {output_file}.")