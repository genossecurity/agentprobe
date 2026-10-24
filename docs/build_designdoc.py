from reportlab.lib.pagesizes import letter
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                HRFlowable, ListFlowable, ListItem, KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

ACC = colors.HexColor("#1F3A5F")
ACC2 = colors.HexColor("#2457c5")
MUT = colors.HexColor("#555555")
CODEBG = colors.HexColor("#f2f4f8")

doc = SimpleDocTemplate("/home/claude/agentprobe/docs/AgentProbe_Design.pdf", pagesize=letter,
    leftMargin=0.7*inch, rightMargin=0.7*inch, topMargin=0.6*inch, bottomMargin=0.6*inch,
    title="AgentProbe - Design", author="Ahmed Khan")
W = letter[0]-1.4*inch

h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=ACC)
tag = ParagraphStyle("tag", fontName="Helvetica", fontSize=10.5, leading=14, textColor=MUT)
H = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=ACC, spaceBefore=12, spaceAfter=2)
body = ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=4)
bul = ParagraphStyle("u", parent=body, leftIndent=12, spaceAfter=1.5)
code = ParagraphStyle("c", fontName="Courier", fontSize=8.2, leading=10.5, textColor=colors.HexColor("#14233a"),
                      backColor=CODEBG, borderPadding=6, spaceBefore=3, spaceAfter=6)
cap = ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=MUT, spaceAfter=6)

S = []
def sec(t): S.append(Paragraph(t, H)); S.append(HRFlowable(width="100%", thickness=0.6, color=ACC, spaceBefore=1, spaceAfter=4))
def bullets(items): return ListFlowable([ListItem(Paragraph(i, bul), leftIndent=10, value="•") for i in items], bulletType="bullet", start="•")

S += [Paragraph("AgentProbe", h1),
      Paragraph("A defensive evaluation harness for LLM-agent prompt-injection resistance &nbsp;·&nbsp; Design note v0.1 &nbsp;·&nbsp; Ahmed Khan", tag),
      Spacer(1,6)]

sec("1. Problem")
S.append(Paragraph(
 "LLM agents feed untrusted content &mdash; web pages, documents, tool results &mdash; back into the model's context. "
 "An attacker who controls that content can attempt <b>indirect prompt injection</b>: steer the agent into leaking data or "
 "invoking a privileged tool. Defenses exist (input/output filters, tool allowlists, human-in-the-loop, trusted/untrusted "
 "context separation), but a control is only worth shipping if you can show it lowers the attack success rate. AgentProbe "
 "measures that, with reproducible numbers, for an agent you own.", body))
S.append(Paragraph("<b>Hypothesis under test:</b> for a given target agent, each defense produces a measurable, "
 "category-specific drop in attack success rate (ASR); some defenses stop one attack class while leaving another untouched.", body))

sec("2. Scope and safety")
S.append(Paragraph("AgentProbe is strictly defensive and is designed so it cannot double as an attack tool:", body))
S.append(bullets([
 "<b>Canary, not payload.</b> Every probe tries to make the agent reveal a random benign token (AGENTPROBE-CANARY-&lt;uuid&gt;). There is no real secret to steal.",
 "<b>Stubbed sensitive action.</b> The privileged tool records an attempted call and sends nothing.",
 "<b>No live endpoints.</b> web_fetch reads only local fixtures; the harness makes no outbound calls on a probe's behalf.",
 "<b>Local-first.</b> The default run is fully offline against a deterministic mock model.",
]))

sec("3. Architecture")
S.append(Paragraph("Five components, each independently testable:", body))
arch = [
 ["Component", "Module", "Responsibility"],
 ["Probe library", "attacks/library.py", "Injection strings + metadata (OWASP LLM, ATLAS, goal, channel)"],
 ["Target agent", "target/agent.py", "Minimal ReAct loop: model → tool → result → repeat"],
 ["Tools", "target/tools.py", "read_file, web_fetch, stubbed send_message (+ call ledger)"],
 ["Defenses", "target/defenses.py", "Six toggleable controls applied around the loop"],
 ["Oracles", "oracles/__init__.py", "Deterministic canary-leak + forbidden-call detectors"],
 ["Runner / report", "runner.py, report.py", "N trials × models × defenses → JSON → ASR tables"],
]
t = Table(arch, colWidths=[W*0.17, W*0.24, W*0.59])
t.setStyle(TableStyle([
 ("BACKGROUND",(0,0),(-1,0),ACC),("TEXTCOLOR",(0,0),(-1,0),colors.white),
 ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.3),
 ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),("FONTNAME",(1,1),(1,-1),"Courier"),
 ("FONTSIZE",(1,1),(1,-1),7.6),
 ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#eef1f6")]),
 ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#c7cfda")),
 ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
 ("LEFTPADDING",(0,0),(-1,-1),5)]))
S.append(t)
S.append(Spacer(1,4))
S.append(Paragraph("Data flow:", body))
S.append(Paragraph(
 "probe &rarr; injected into a tool&#39;s output/description &rarr; target agent (ReAct) &rarr; tool calls &amp; final answer<br/>"
 "&nbsp;&nbsp;&nbsp;&nbsp;&rarr; oracle: canary leaked? forbidden tool called? &rarr; verdict &rarr; ASR aggregation", code))

sec("4. Threat model and probe taxonomy")
S.append(Paragraph("Each probe declares a goal (leak a token, or act via a forbidden tool call) and the channel it rides "
 "in (tool result, document, or a poisoned tool description). Probes are mapped to industry frameworks so results speak "
 "the language a security reviewer expects:", body))
tax = [
 ["Probe category", "Goal", "Channel", "OWASP LLM / ATLAS"],
 ["instruction_override", "leak", "tool result / doc", "LLM01 / AML.T0051"],
 ["exfiltration_via_tool", "act", "document", "LLM01 / AML.T0057"],
 ["tool_poisoning", "act", "tool description", "LLM01 / AML.T0051.000"],
 ["excessive_agency", "act", "tool result", "LLM06 / AML.T0053"],
 ["obfuscation (evasion)", "leak", "document", "LLM01 / AML.T0051"],
 ["control_no_attack", "—", "document", "n/a (false-positive guard)"],
]
t2 = Table(tax, colWidths=[W*0.27, W*0.11, W*0.26, W*0.36])
t2.setStyle(TableStyle([
 ("BACKGROUND",(0,0),(-1,0),ACC2),("TEXTCOLOR",(0,0),(-1,0),colors.white),
 ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.3),
 ("FONTNAME",(0,1),(0,-1),"Courier"),("FONTSIZE",(0,1),(0,-1),7.6),
 ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#eef1f6")]),
 ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#c7cfda")),
 ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),5)]))
S.append(t2)

sec("5. Evaluation methodology")
S.append(bullets([
 "<b>Deterministic oracles.</b> Success is decided by string + state checks (canary present, or send_message called with the canary), never by an LLM judge that could itself be injected.",
 "<b>Multiple trials per cell.</b> Model output is nondeterministic, so ASR is averaged over N trials for every (probe × model × defense) cell.",
 "<b>Baselines.</b> Every defense is compared against the 'none' configuration to compute a per-category ASR drop.",
 "<b>Negative control.</b> A benign probe must never fire the oracle; it catches false positives in the oracle or filters.",
 "<b>Cross-model.</b> The same matrix runs across a local model (Ollama) and an API model via a one-method adapter.",
]))

sec("6. Sample result (mock target, 5 trials/cell)")
S.append(Paragraph("The bundled mock models a naively susceptible agent, giving a non-trivial baseline so defenses show a "
 "visible drop. Representative output from <font face='Courier'>python -m agentprobe report</font>:", body))
res = [
 ["Defense config", "Overall ASR", "Reading"],
 ["none", "83%", "Baseline: most probes succeed"],
 ["input_filter", "17%", "Pattern-strips injected instructions in tool output"],
 ["output_filter", "17%", "Blocks the canary from leaving in the answer"],
 ["allowlist", "67%", "Stops tool-call attacks only; leaks still pass"],
 ["context_tagging (alone)", "83%", "Delimiters alone don't stop a compliant model"],
 ["all", "0%", "Layered controls close every category"],
]
t3 = Table(res, colWidths=[W*0.30, W*0.16, W*0.54])
t3.setStyle(TableStyle([
 ("BACKGROUND",(0,0),(-1,0),ACC),("TEXTCOLOR",(0,0),(-1,0),colors.white),
 ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),
 ("FONTNAME",(0,1),(0,-1),"Courier"),("FONTSIZE",(0,1),(0,-1),8),
 ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#eef1f6")]),
 ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#c7cfda")),
 ("TEXTCOLOR",(1,1),(1,1),colors.HexColor("#c2412d")),("FONTNAME",(1,1),(1,1),"Courier-Bold"),
 ("TEXTCOLOR",(1,6),(1,6),colors.HexColor("#1b7a3d")),("FONTNAME",(1,6),(1,6),"Courier-Bold"),
 ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),5)]))
S.append(t3)
S.append(Paragraph("The interesting finding is not the 0%; it is the middle rows. A tool allowlist stops exfiltration-by-tool "
 "but does nothing for a plain data leak, and context tagging alone barely moves ASR against a compliant model. That is the "
 "kind of per-control, per-category evidence a security team needs before trusting one guardrail in production.", cap))

sec("7. Roadmap")
S.append(bullets([
 "Real model adapters (Ollama + one API model) and a cross-model ASR comparison.",
 "MCP transport target: run the same probes against a real MCP server/client boundary.",
 "Expand the probe library (multi-turn, memory/RAG poisoning) while keeping payloads at canary level.",
 "CI gate: fail a build if a defended configuration's ASR rises above a threshold.",
]))
S.append(Spacer(1,4))
S.append(Paragraph("Repository layout, quick-start, and the full probe set are in README.md; safety constraints in SECURITY.md.", cap))

doc.build(S)
print("built")
