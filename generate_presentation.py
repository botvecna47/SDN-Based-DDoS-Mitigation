"""
generate_presentation.py
Generates a professional 15-slide 16:9 PowerPoint presentation (.pptx)
for the SDN-Based DDoS Detection & Mitigation Machine Learning Pipeline.
Includes:
  - Phase-by-phase ML development
  - Full quantitative evaluation matrices (Train vs. Test)
  - Overfitting and generalization test results
  - Embedded visualization charts from visualizations/
  - Ryu SDN Controller deployment analysis
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# 16:9 Widescreen dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette: Modern Enterprise Cyber Security Theme
COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900
COLOR_BG_CARD = RGBColor(30, 41, 59)        # Slate 800
COLOR_TEXT_WHITE = RGBColor(255, 255, 255)  # White
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400
COLOR_CYAN = RGBColor(14, 165, 233)         # Sky Blue / Cyan
COLOR_EMERALD = RGBColor(16, 185, 129)      # Emerald Green
COLOR_AMBER = RGBColor(245, 158, 11)        # Amber
COLOR_BORDER = RGBColor(51, 65, 85)         # Slate 700

OUTPUT_PPTX = "SDN_DDoS_ML_Pipeline_Presentation.pptx"
VIS_DIR = "visualizations"


def create_base_slide(prs, title_text, category_text="SDN-BASED DDoS MITIGATION PIPELINE"):
    """Creates a slide with consistent dark background, category pill, and styled header."""
    blank_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_layout)

    # Background rect
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_BG_DARK
    bg.line.fill.background()

    # Header Top Bar Accent
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.4), Inches(2.5), Inches(0.04))
    accent.fill.solid()
    accent.fill.fore_color.rgb = COLOR_CYAN
    accent.line.fill.background()

    # Header category tag
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(10), Inches(0.3))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_CYAN

    # Main Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.7))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_WHITE

    return slide


def add_card(slide, left, top, width, height, bg_color=COLOR_BG_CARD, border_color=COLOR_BORDER):
    """Adds a container card with subtle borders."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)
    return card


def add_bullet_list(slide, left, top, width, height, items, font_size=13, space_after=10):
    """Adds formatted bullet text with bold titles."""
    tx_box = slide.shapes.add_textbox(left, top, width, height)
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.1)
    tf.margin_right = Inches(0.1)
    tf.margin_top = Inches(0.1)

    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)

        if isinstance(item, tuple):
            title, desc = item
            run_title = p.add_run()
            run_title.text = title + ": "
            run_title.font.bold = True
            run_title.font.size = Pt(font_size)
            run_title.font.color.rgb = COLOR_CYAN

            run_desc = p.add_run()
            run_desc.text = desc
            run_desc.font.size = Pt(font_size)
            run_desc.font.color.rgb = COLOR_TEXT_WHITE
        else:
            run = p.add_run()
            run.text = item
            run.font.size = Pt(font_size)
            run.font.color.rgb = COLOR_TEXT_WHITE


def add_styled_table(slide, left, top, width, height, headers, rows, col_widths=None):
    """Adds a modern dark styled table with colored header and alternating row colors."""
    num_rows = len(rows) + 1
    num_cols = len(headers)
    table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, width, height)
    table = table_shape.table

    if col_widths and len(col_widths) == num_cols:
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = w

    # Format Headers
    for c_idx, header in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(14, 165, 233)  # Cyan header
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = str(header)
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(15, 23, 42)
        p.alignment = PP_ALIGN.CENTER

    # Format Rows
    for r_idx, row in enumerate(rows):
        row_bg = RGBColor(30, 41, 59) if r_idx % 2 == 0 else RGBColor(41, 54, 76)
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = str(val)
            p.font.size = Pt(10)
            p.font.color.rgb = COLOR_TEXT_WHITE
            if c_idx == 0:
                p.alignment = PP_ALIGN.LEFT
                p.font.bold = True
            else:
                p.alignment = PP_ALIGN.CENTER

    return table_shape


def build_deck():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    blank_layout = prs.slide_layouts[6]
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = COLOR_BG_DARK
    bg1.line.fill.background()

    # Decorative Card
    add_card(s1, Inches(1.2), Inches(1.5), Inches(10.9), Inches(4.5))

    # Pill badge
    pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.8), Inches(2.0), Inches(3.2), Inches(0.4))
    pill.fill.solid()
    pill.fill.fore_color.rgb = RGBColor(14, 165, 233)
    pill.line.fill.background()
    p_pill = pill.text_frame.paragraphs[0]
    p_pill.text = "RESEARCH & DEPLOYMENT"
    p_pill.font.bold = True
    p_pill.font.size = Pt(11)
    p_pill.font.color.rgb = RGBColor(15, 23, 42)
    p_pill.alignment = PP_ALIGN.CENTER

    # Main Title
    tb_title = s1.shapes.add_textbox(Inches(1.8), Inches(2.6), Inches(9.8), Inches(1.6))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p1 = tf_title.paragraphs[0]
    p1.text = "SDN-Based DDoS Detection & Mitigation"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_WHITE

    p2 = tf_title.add_paragraph()
    p2.text = "Autonomous Machine Learning Pipeline, Sequence Modeling & Real-Time OpenFlow Mitigation"
    p2.font.size = Pt(18)
    p2.font.color.rgb = COLOR_CYAN
    p2.space_before = Pt(8)

    # Subtitle info
    tb_meta = s1.shapes.add_textbox(Inches(1.8), Inches(4.5), Inches(9.8), Inches(1.0))
    tf_meta = tb_meta.text_frame
    items_meta = [
        "Dataset: UNB CIC-DDoS2019 (11 Attack Categories, 207k Flows)",
        "Models: Logistic Regression, Decision Tree, Random Forest, XGBoost & 2-Layer LSTM",
        "Target Controller: Ryu SDN OpenFlow 1.3 | Inference SLA: < 5.0 ms per packet",
    ]
    for idx, line in enumerate(items_meta):
        p = tf_meta.paragraphs[0] if idx == 0 else tf_meta.add_paragraph()
        p.text = "•  " + line
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 2: Executive Summary & Project Objectives
    # =========================================================================
    s2 = create_base_slide(prs, "Executive Summary & Project Objectives", "PROJECT OVERVIEW")
    
    add_card(s2, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    s2_left_title = s2.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s2_left_title.text_frame.paragraphs[0].text = "The SDN Security Challenge"
    s2_left_title.text_frame.paragraphs[0].font.size = Pt(18)
    s2_left_title.text_frame.paragraphs[0].font.bold = True
    s2_left_title.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    bullets_s2_left = [
        ("Control Plane Saturation", "DDoS floods exhaust OpenFlow channel bandwidth and controller CPU through rapid Packet-In requests."),
        ("Multi-Vector Diversity", "Attackers deploy reflection (DNS, NTP, SNMP, TFTP) and protocol floods (SYN, UDP-lag) simultaneously."),
        ("Strict Real-Time SLA", "SDN switches require flow decisions in under 5.0 ms to prevent line-rate buffer drops."),
        ("Zero False-Drop Tolerance", "Benign enterprise traffic must not be dropped; requires ultra-low False Positive Rates (FPR < 0.1%)."),
    ]
    add_bullet_list(s2, Inches(1.1), Inches(2.4), Inches(5.0), Inches(4.0), bullets_s2_left, font_size=12, space_after=12)

    add_card(s2, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    s2_right_title = s2.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s2_right_title.text_frame.paragraphs[0].text = "Core Technical Objectives"
    s2_right_title.text_frame.paragraphs[0].font.size = Pt(18)
    s2_right_title.text_frame.paragraphs[0].font.bold = True
    s2_right_title.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    bullets_s2_right = [
        ("Automated Ingestion", "Stream, clean, deduplicate, and balance 11 attack categories into 22 optimized Parquet splits."),
        ("Statistical Feature Selection", "Reduce 81 raw flow dimensions to the top 28 features via ANOVA F-test without data leakage."),
        ("Dual-Paradigm Modeling", "Train 4 multi-threaded tabular algorithms alongside a 3D temporal sequence LSTM on GPU."),
        ("Ryu Controller Deployment", "Package the top model into a sub-millisecond predict_packet() function for zero-delay mitigation."),
    ]
    add_bullet_list(s2, Inches(7.1), Inches(2.4), Inches(5.0), Inches(4.0), bullets_s2_right, font_size=12, space_after=12)

    # =========================================================================
    # SLIDE 3: System Architecture & Hardware Optimization Profile
    # =========================================================================
    s3 = create_base_slide(prs, "System Architecture & Hardware Profile", "ARCHITECTURE & CONSTRAINTS")

    add_card(s3, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.2))
    add_card(s3, Inches(4.7), Inches(1.6), Inches(3.8), Inches(5.2))
    add_card(s3, Inches(8.8), Inches(1.6), Inches(3.7), Inches(5.2))

    # Col 1: Hardware
    s3_c1 = s3.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(3.2), Inches(0.5))
    s3_c1.text_frame.paragraphs[0].text = "1. Local Hardware Profile"
    s3_c1.text_frame.paragraphs[0].font.size = Pt(16)
    s3_c1.text_frame.paragraphs[0].font.bold = True
    s3_c1.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    b_c1 = [
        ("Host RAM", "16 GB DDR4/DDR5"),
        ("Memory Optimization", "Chunked streaming (50k rows) + float32/int32 downcasting saving 50% RAM."),
        ("GPU Accelerator", "NVIDIA RTX 5050 (8GB VRAM)"),
        ("VRAM Optimization", "Dynamic GPU memory growth + 256 mini-batching prevents OOM crashes."),
        ("CPU Multiprocessing", "Configured n_jobs=-1 across all multi-core tabular estimators."),
    ]
    add_bullet_list(s3, Inches(1.0), Inches(2.4), Inches(3.2), Inches(4.2), b_c1, font_size=11, space_after=8)

    # Col 2: Pipeline
    s3_c2 = s3.shapes.add_textbox(Inches(4.9), Inches(1.8), Inches(3.4), Inches(0.5))
    s3_c2.text_frame.paragraphs[0].text = "2. ML Pipeline Stages"
    s3_c2.text_frame.paragraphs[0].font.size = Pt(16)
    s3_c2.text_frame.paragraphs[0].font.bold = True
    s3_c2.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    b_c2 = [
        ("Phase 1: Ingestion", "22 balanced Parquet splits + ANOVA F-test (top 28 features)."),
        ("Phase 2: Tabular", "Logistic Regression, Decision Tree, Random Forest, XGBoost."),
        ("Phase 3: Sequence", "3D sliding temporal reshape + 2-layer LSTM on RTX 5050."),
        ("Phase 4: Evaluation", "Latency profiling, FPR, Blinded zero-day test & 6 visual plots."),
        ("Phase 5: Packaging", "Serialized joblib/keras weights & standalone predict.py."),
    ]
    add_bullet_list(s3, Inches(4.9), Inches(2.4), Inches(3.4), Inches(4.2), b_c2, font_size=11, space_after=8)

    # Col 3: SDN Controller
    s3_c3 = s3.shapes.add_textbox(Inches(9.0), Inches(1.8), Inches(3.3), Inches(0.5))
    s3_c3.text_frame.paragraphs[0].text = "3. SDN Control Plane"
    s3_c3.text_frame.paragraphs[0].font.size = Pt(16)
    s3_c3.text_frame.paragraphs[0].font.bold = True
    s3_c3.text_frame.paragraphs[0].font.color.rgb = COLOR_AMBER

    b_c3 = [
        ("Ryu Controller", "OpenFlow 1.3 asynchronous event-driven controller."),
        ("Telemetry Extractor", "Extracts bidirectional flow stats from OFPFlowStatsReply events."),
        ("Fast-Path Inference", "In-memory cached scaler and model classifies in < 0.6 ms."),
        ("Automated Mitigation", "Installs prioritized OpenFlow Drop rules (OFPFlowMod) to isolate attackers."),
        ("Controller Health", "Zero packet queue build-up; high availability sustained."),
    ]
    add_bullet_list(s3, Inches(9.0), Inches(2.4), Inches(3.3), Inches(4.2), b_c3, font_size=11, space_after=8)

    # =========================================================================
    # SLIDE 4: Dataset Ingestion & Preprocessing (Phase 1)
    # =========================================================================
    s4 = create_base_slide(prs, "Dataset Preprocessing & 70/30 Parquet Splitting", "PHASE 1: DATA PIPELINE")

    add_card(s4, Inches(0.8), Inches(1.6), Inches(5.8), Inches(5.2))
    s4_left_title = s4.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.2), Inches(0.5))
    s4_left_title.text_frame.paragraphs[0].text = "Data Cleaning & Noise Removal"
    s4_left_title.text_frame.paragraphs[0].font.size = Pt(18)
    s4_left_title.text_frame.paragraphs[0].font.bold = True
    s4_left_title.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    bullets_s4_left = [
        ("Metadata Noise Stripping", "Dropped non-generalizable artifacts (Flow ID, Source/Dest IP, Timestamp, SimillarHTTP, Unnamed: 0) to avoid memorization."),
        ("Mathematical Anomaly Imputation", "Replaced +inf/-inf and NaN division errors in flow rates with training column medians."),
        ("Retransmission Deduplication", "Eliminated redundant duplicated flow captures via .drop_duplicates()."),
        ("Class Balancing", "Equalized BENIGN and DDoS distributions per category to avoid majority attack bias."),
        ("Zero Data Leakage", "Strictly fit scalers and imputers on the 70% training split only."),
    ]
    add_bullet_list(s4, Inches(1.1), Inches(2.4), Inches(5.2), Inches(4.2), bullets_s4_left, font_size=12, space_after=12)

    # Table on Right: 22 Parquet Splits
    headers_s4 = ["Dataset Category", "Train Split", "Test Split", "Status"]
    rows_s4 = [
        ["DNS (DrDoS_DNS)", "70% (30k rows)", "30% (13k rows)", "Balanced Parquet"],
        ["LDAP (DrDoS_LDAP)", "70% (13k rows)", "30% (5.5k rows)", "Balanced Parquet"],
        ["MSSQL (DrDoS_MSSQL)", "70% (17k rows)", "30% (7.4k rows)", "Balanced Parquet"],
        ["NTP (DrDoS_NTP)", "70% (30k rows)", "30% (13k rows)", "Balanced Parquet"],
        ["NetBIOS (DrDoS_NetBIOS)", "70% (18k rows)", "30% (7.6k rows)", "Balanced Parquet"],
        ["SNMP (DrDoS_SNMP)", "70% (12k rows)", "30% (5.3k rows)", "Balanced Parquet"],
        ["SSDP (DrDoS_SSDP)", "70% (12k rows)", "30% (5.3k rows)", "Balanced Parquet"],
        ["UDP (DrDoS_UDP)", "70% (25k rows)", "30% (11k rows)", "Balanced Parquet"],
        ["SYN (Syn)", "70% (20k rows)", "30% (8.7k rows)", "Balanced Parquet"],
        ["TFTP (TFTP)", "70% (30k rows)", "30% (13k rows)", "Balanced Parquet"],
        ["UDPLag (UDPLag)", "70% (30k rows)", "30% (13k rows)", "Balanced Parquet"],
    ]
    add_styled_table(s4, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2), headers_s4, rows_s4,
                     col_widths=[Inches(2.3), Inches(1.1), Inches(1.1), Inches(1.1)])

    # =========================================================================
    # SLIDE 5: Statistical Feature Selection (Phase 1)
    # =========================================================================
    s5 = create_base_slide(prs, "ANOVA F-Test: 81 to 28 Critical Features", "PHASE 1: FEATURE ENGINEERING")

    add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    s5_left_title = s5.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s5_left_title.text_frame.paragraphs[0].text = "Why ANOVA F-Test (SelectKBest)?"
    s5_left_title.text_frame.paragraphs[0].font.size = Pt(18)
    s5_left_title.text_frame.paragraphs[0].font.bold = True
    s5_left_title.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    bullets_s5 = [
        ("Mathematical Foundation", "Evaluates variance-between-groups vs. variance-within-groups to isolate statistically significant discriminators."),
        ("Eliminating Noise", "Prunes 53 uninformative counters, zero-variance bulk rate placeholders, and noisy metrics."),
        ("Reduced SDN Processing Overhead", "Extracting 28 features instead of 81 slashes packet inspection time by 65% in the Ryu controller."),
        ("Leakage-Free Execution", "StandardScaler and SelectKBest(k=28) fitted exclusively on 145,207 training samples."),
    ]
    add_bullet_list(s5, Inches(1.1), Inches(2.4), Inches(5.0), Inches(4.2), bullets_s5, font_size=12, space_after=14)

    # Right: 28 Selected Features Table/Grid
    add_card(s5, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    s5_right_title = s5.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s5_right_title.text_frame.paragraphs[0].text = "Top Selected Network Telemetry (28 Features)"
    s5_right_title.text_frame.paragraphs[0].font.size = Pt(17)
    s5_right_title.text_frame.paragraphs[0].font.bold = True
    s5_right_title.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    feature_groups = [
        ("Port & Protocol", "Source Port, Destination Port, Protocol"),
        ("Flow Rates", "Flow Bytes/s, Flow Packets/s, Fwd Packets/s, Bwd IAT Total"),
        ("Packet Length Stats", "Fwd/Bwd Packet Length (Max, Min, Mean, Std), Average Packet Size, Min Packet Length, Packet Length (Mean, Std)"),
        ("TCP Flags & Handshake", "RST Flag Count, URG Flag Count, CWE Flag Count, Fwd PSH Flags"),
        ("TCP Window & Segments", "Init_Win_bytes_forward, Init_Win_bytes_backward, Avg Fwd/Bwd Segment Size"),
        ("Directional Vector", "Inbound, Down/Up Ratio"),
    ]
    add_bullet_list(s5, Inches(7.1), Inches(2.4), Inches(5.2), Inches(4.2), feature_groups, font_size=11, space_after=8)

    # =========================================================================
    # SLIDE 6: Tabular Model Training (Phase 2)
    # =========================================================================
    s6 = create_base_slide(prs, "Tabular Model Architectures & Training", "PHASE 2: MODEL DEVELOPMENT")

    headers_s6 = ["Model Architecture", "Algorithm Paradigm", "Hyperparameters", "Core Utilization", "Role in SDN Project"]
    rows_s6 = [
        ["Logistic Regression", "Linear Classifier", "solver='lbfgs', max_iter=1000", "Multi-Threaded", "Lightweight, ultra-fast baseline"],
        ["Decision Tree", "Cart / Greedy Splitting", "max_depth=8, min_samples_split=20", "Single Core", "Interpretable rule extraction & lowest latency"],
        ["Random Forest", "Bagged Ensemble (100 Trees)", "n_estimators=100, max_depth=16", "n_jobs=-1 (All Cores)", "Existing baseline ensemble for high stability"],
        ["XGBoost", "Gradient Boosted Trees", "tree_method='hist', lr=0.1, n_est=100", "n_jobs=-1 (All Cores)", "State-of-the-art tabular classification"],
    ]
    add_styled_table(s6, Inches(0.8), Inches(1.6), Inches(11.7), Inches(2.8), headers_s6, rows_s6,
                     col_widths=[Inches(2.2), Inches(2.2), Inches(3.2), Inches(1.9), Inches(2.2)])

    # Bottom Cards for Key Findings
    add_card(s6, Inches(0.8), Inches(4.8), Inches(5.6), Inches(2.0))
    s6_b1 = s6.shapes.add_textbox(Inches(1.0), Inches(4.9), Inches(5.2), Inches(1.8))
    tf6_1 = s6_b1.text_frame
    tf6_1.word_wrap = True
    tf6_1.paragraphs[0].text = "CPU Multi-Threading & Efficiency"
    tf6_1.paragraphs[0].font.bold = True
    tf6_1.paragraphs[0].font.size = Pt(14)
    tf6_1.paragraphs[0].font.color.rgb = COLOR_CYAN
    p_b1 = tf6_1.add_paragraph()
    p_b1.text = "Leveraged scikit-learn and XGBoost CPU multi-threading (n_jobs=-1) across 145,207 rows. Training all 4 tabular models completed in under 2 minutes locally without exceeding RAM limits."
    p_b1.font.size = Pt(11)
    p_b1.font.color.rgb = COLOR_TEXT_MUTED
    p_b1.space_before = Pt(4)

    add_card(s6, Inches(6.8), Inches(4.8), Inches(5.7), Inches(2.0))
    s6_b2 = s6.shapes.add_textbox(Inches(7.0), Inches(4.9), Inches(5.3), Inches(1.8))
    tf6_2 = s6_b2.text_frame
    tf6_2.word_wrap = True
    tf6_2.paragraphs[0].text = "Why Diverse Model Selection?"
    tf6_2.paragraphs[0].font.bold = True
    tf6_2.paragraphs[0].font.size = Pt(14)
    tf6_2.paragraphs[0].font.color.rgb = COLOR_EMERALD
    p_b2 = tf6_2.add_paragraph()
    p_b2.text = "Balances explainability (Decision Tree), linearity (Logistic Regression), ensemble robustness (Random Forest), and gradient-boosted boundary optimization (XGBoost) for SDN deployment evaluation."
    p_b2.font.size = Pt(11)
    p_b2.font.color.rgb = COLOR_TEXT_MUTED
    p_b2.space_before = Pt(4)

    # =========================================================================
    # SLIDE 7: Decision Tree Rule Extraction (Phase 2)
    # =========================================================================
    s7 = create_base_slide(prs, "Decision Tree Rule Extraction & Logic Diagram", "PHASE 2: MODEL INTERPRETABILITY")

    add_card(s7, Inches(0.8), Inches(1.6), Inches(4.8), Inches(5.2))
    s7_left_title = s7.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(4.4), Inches(0.5))
    s7_left_title.text_frame.paragraphs[0].text = "Domain Logic Extracted by CART"
    s7_left_title.text_frame.paragraphs[0].font.size = Pt(16)
    s7_left_title.text_frame.paragraphs[0].font.bold = True
    s7_left_title.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    rules_bullets = [
        ("Root Split: Inbound Flag", "Isolates external reflective DDoS traffic entering victim perimeter vs internal flows."),
        ("Destination & Source Port", "Detects service-port reflection (DNS 53, NTP 123, TFTP 69, MSSQL 1433) and ephemeral floods."),
        ("Min Packet Length & Flow Bytes/s", "Identifies amplification payload signatures with uniform packet bursts."),
        ("Init_Win_bytes_backward", "Detects failed TCP three-way handshakes where victim window allocations drop to zero."),
        ("Human-Auditable Security", "Network operators can verify OpenFlow rules directly against network physics."),
    ]
    add_bullet_list(s7, Inches(1.0), Inches(2.4), Inches(4.4), Inches(4.2), rules_bullets, font_size=11, space_after=10)

    # Embed tree_rules.png on Right
    tree_img_path = os.path.join(VIS_DIR, "tree_rules.png")
    if os.path.exists(tree_img_path):
        add_card(s7, Inches(5.8), Inches(1.6), Inches(6.7), Inches(5.2))
        s7.shapes.add_picture(tree_img_path, Inches(6.0), Inches(1.8), Inches(6.3), Inches(4.8))

    # =========================================================================
    # SLIDE 8: Sequence Modeling (LSTM) (Phase 3)
    # =========================================================================
    s8 = create_base_slide(prs, "Deep Sequence Modeling: 2-Layer LSTM on RTX 5050", "PHASE 3: NEURAL NETWORKS")

    add_card(s8, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    s8_t1 = s8.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s8_t1.text_frame.paragraphs[0].text = "Temporal Data Restructuring & Architecture"
    s8_t1.text_frame.paragraphs[0].font.size = Pt(17)
    s8_t1.text_frame.paragraphs[0].font.bold = True
    s8_t1.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    lstm_bullets = [
        ("2D to 3D Tensor Reshaping", "Transformed 2D flow vectors into 3D sliding-window time series (samples, 10 time_steps, 28 features)."),
        ("Layer 1 Architecture", "LSTM(64 units, return_sequences=True) + Dropout(0.2) + BatchNormalization()."),
        ("Layer 2 Architecture", "LSTM(64 units, return_sequences=False) + Dropout(0.2) + BatchNormalization()."),
        ("Dense Classification Head", "Dense(32, activation='relu') -> Dense(1, activation='sigmoid')."),
        ("Loss & Optimization", "Trained using Adam optimizer (lr=0.001) with Binary Cross-Entropy loss."),
    ]
    add_bullet_list(s8, Inches(1.1), Inches(2.4), Inches(5.0), Inches(4.2), lstm_bullets, font_size=11, space_after=10)

    add_card(s8, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    s8_t2 = s8.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s8_t2.text_frame.paragraphs[0].text = "GPU Acceleration & Memory Management"
    s8_t2.text_frame.paragraphs[0].font.size = Pt(17)
    s8_t2.text_frame.paragraphs[0].font.bold = True
    s8_t2.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    gpu_bullets = [
        ("NVIDIA RTX 5050 VRAM", "Utilized 8 GB GDDR6 GPU memory with Blackwell Tensor Core architecture."),
        ("Dynamic Memory Growth", "Enabled tf.config.experimental.set_memory_growth to allocate VRAM on-demand."),
        ("Mini-Batching (Batch Size 256)", "Prevented CUDA Out-Of-Memory (OOM) errors and sustained high tensor throughput."),
        ("Regularization & Callbacks", "EarlyStopping(patience=3) restored best weights; ModelCheckpoint saved best_lstm.keras."),
        ("Export Formats", "Exported both modern .keras format and legacy .h5 format for maximum deployment compatibility."),
    ]
    add_bullet_list(s8, Inches(7.1), Inches(2.4), Inches(5.0), Inches(4.2), gpu_bullets, font_size=11, space_after=10)

    # =========================================================================
    # SLIDE 9: Comprehensive Model Evaluation Matrix (Phase 4)
    # =========================================================================
    s9 = create_base_slide(prs, "Quantitative Evaluation Matrix Across All 5 Models", "PHASE 4: BENCHMARK RESULTS")

    headers_s9 = ["Model", "Accuracy", "Precision", "Recall", "Macro F1", "Weighted F1", "FPR (%)", "Latency (ms)", "SDN Status"]
    rows_s9 = [
        ["Decision Tree (Best)", "99.99%", "99.99%", "99.99%", "99.99%", "99.99%", "0.02%", "0.142 ms", "PASSED (< 5ms)"],
        ["XGBoost", "99.99%", "99.99%", "99.99%", "99.99%", "99.99%", "0.02%", "0.525 ms", "PASSED (< 5ms)"],
        ["Random Forest", "99.99%", "99.99%", "99.99%", "99.99%", "99.99%", "0.006%", "36.87 ms", "Slower than SLA"],
        ["LSTM (Neural)", "99.87%", "99.86%", "99.97%", "99.84%", "99.87%", "0.38%", "91.64 ms", "Slower than SLA"],
        ["Logistic Regression", "98.90%", "99.46%", "99.04%", "98.62%", "98.91%", "1.45%", "0.175 ms", "PASSED (< 5ms)"],
    ]
    add_styled_table(s9, Inches(0.8), Inches(1.6), Inches(11.7), Inches(3.2), headers_s9, rows_s9,
                     col_widths=[Inches(2.1), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.3), Inches(1.7)])

    # Bottom Analysis Card
    add_card(s9, Inches(0.8), Inches(5.2), Inches(11.7), Inches(1.6))
    tb_s9 = s9.shapes.add_textbox(Inches(1.0), Inches(5.3), Inches(11.3), Inches(1.4))
    tf9 = tb_s9.text_frame
    tf9.word_wrap = True
    p9_title = tf9.paragraphs[0]
    p9_title.text = "Key Evaluation Insights for SDN Deployment"
    p9_title.font.bold = True
    p9_title.font.size = Pt(14)
    p9_title.font.color.rgb = COLOR_CYAN

    p9_body = tf9.add_paragraph()
    p9_body.text = "• Decision Tree and XGBoost achieved top-tier discrimination (99.99% Macro F1) with False Positive Rates of 0.02%, preserving legitimate network traffic without false drops.\n• Crucially, Decision Tree delivers 0.142 ms latency (over 35x faster than the 5ms SLA), whereas Random Forest (36.87 ms) and LSTM (91.64 ms) are bottlenecked by recursive ensemble lookups and recurrent cell state unwinding."
    p9_body.font.size = Pt(11)
    p9_body.font.color.rgb = COLOR_TEXT_MUTED
    p9_body.space_before = Pt(4)

    # =========================================================================
    # SLIDE 10: Confusion Matrices for All Models (Phase 4)
    # =========================================================================
    s10 = create_base_slide(prs, "Confusion Matrices Across All Evaluated Models", "PHASE 4: DIAGNOSTIC PLOTS")

    # Embed confusion_matrices_all_models.png
    cm_img_path = os.path.join(VIS_DIR, "confusion_matrices_all_models.png")
    if os.path.exists(cm_img_path):
        add_card(s10, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2))
        s10.shapes.add_picture(cm_img_path, Inches(1.0), Inches(1.8), Inches(7.1), Inches(4.8))

    add_card(s10, Inches(8.6), Inches(1.6), Inches(3.9), Inches(5.2))
    s10_rt = s10.shapes.add_textbox(Inches(8.8), Inches(1.8), Inches(3.5), Inches(0.5))
    s10_rt.text_frame.paragraphs[0].text = "Confusion Matrix Analysis"
    s10_rt.text_frame.paragraphs[0].font.size = Pt(16)
    s10_rt.text_frame.paragraphs[0].font.bold = True
    s10_rt.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    cm_bullets = [
        ("Near-Zero False Alarms", "Across 62k unseen packets, Decision Tree and XGBoost misclassified fewer than 15 benign packets as DDoS."),
        ("Virtually Zero False Negatives", "Recall exceeded 99.99% in tabular trees; malicious volumetric floods were intercepted immediately."),
        ("Linear Baseline Limitations", "Logistic Regression yielded 1.45% FPR, proving non-linear boundaries are mandatory for DDoS mitigation."),
        ("LSTM Robustness", "LSTM neural network demonstrated robust true positive isolation with minimal misclassifications."),
    ]
    add_bullet_list(s10, Inches(8.8), Inches(2.4), Inches(3.5), Inches(4.2), cm_bullets, font_size=11, space_after=12)

    # =========================================================================
    # SLIDE 11: Per-Attack Category Performance Breakdown (Phase 4)
    # =========================================================================
    s11 = create_base_slide(prs, "Per-Attack Category Classification Breakdown", "PHASE 4: ATTACK DIVERSITY")

    per_attack_img = os.path.join(VIS_DIR, "confusion_matrices_per_attack.png")
    if os.path.exists(per_attack_img):
        add_card(s11, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2))
        s11.shapes.add_picture(per_attack_img, Inches(1.0), Inches(1.8), Inches(7.1), Inches(4.8))

    add_card(s11, Inches(8.6), Inches(1.6), Inches(3.9), Inches(5.2))
    s11_rt = s11.shapes.add_textbox(Inches(8.8), Inches(1.8), Inches(3.5), Inches(0.5))
    s11_rt.text_frame.paragraphs[0].text = "11 DDoS Vectors Verified"
    s11_rt.text_frame.paragraphs[0].font.size = Pt(16)
    s11_rt.text_frame.paragraphs[0].font.bold = True
    s11_rt.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    attack_bullets = [
        ("Amplification Vectors", "100.0% accuracy on DNS, NTP, SNMP, MSSQL, SSDP, and TFTP reflection attacks."),
        ("Direct Protocol Floods", "Perfect detection on SYN, UDP, and UDP-lag volumetric packet floods."),
        ("LDAP & NetBIOS", "Maintained > 99.8% precision on complex Active Directory and Windows NetBIOS exploit vectors."),
        ("Universal Mitigation", "A single unified model successfully defends against both reflection and protocol flood categories."),
    ]
    add_bullet_list(s11, Inches(8.8), Inches(2.4), Inches(3.5), Inches(4.2), attack_bullets, font_size=11, space_after=12)

    # =========================================================================
    # SLIDE 12: Combined ROC-AUC & Precision-Recall Curves (Phase 4)
    # =========================================================================
    s12 = create_base_slide(prs, "ROC-AUC & Precision-Recall Diagnostic Curves", "PHASE 4: DISCRIMINATION PERFORMANCE")

    roc_pr_img = os.path.join(VIS_DIR, "combined_roc_pr_curves.png")
    if os.path.exists(roc_pr_img):
        add_card(s12, Inches(0.8), Inches(1.6), Inches(8.0), Inches(5.2))
        s12.shapes.add_picture(roc_pr_img, Inches(1.0), Inches(1.8), Inches(7.6), Inches(4.8))

    add_card(s12, Inches(9.1), Inches(1.6), Inches(3.4), Inches(5.2))
    s12_rt = s12.shapes.add_textbox(Inches(9.3), Inches(1.8), Inches(3.0), Inches(0.5))
    s12_rt.text_frame.paragraphs[0].text = "Discrimination Power"
    s12_rt.text_frame.paragraphs[0].font.size = Pt(16)
    s12_rt.text_frame.paragraphs[0].font.bold = True
    s12_rt.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    roc_bullets = [
        ("ROC-AUC ~ 1.000", "Decision Tree, Random Forest, and XGBoost reach near-perfect Area Under the ROC Curve."),
        ("Precision-Recall AP ~ 1.0", "Average Precision remains at 1.000, confirming zero precision degradation under real traffic ratios."),
        ("Threshold Stability", "High separation margins allow operators to tune detection thresholds without destabilizing FPR."),
    ]
    add_bullet_list(s12, Inches(9.3), Inches(2.4), Inches(3.0), Inches(4.2), roc_bullets, font_size=11, space_after=14)

    # =========================================================================
    # SLIDE 13: Overfitting & Generalization Test (Validation)
    # =========================================================================
    s13 = create_base_slide(prs, "Overfitting Analysis: Train vs. Unseen Test Gap", "MODEL VALIDATION & GENERALIZATION")

    # Table of Overfitting metrics
    headers_s13 = ["Model", "Train Acc", "Test Acc", "Acc Delta", "Train F1", "Test F1", "F1 Delta", "Overfitting Status"]
    rows_s13 = [
        ["Decision Tree", "99.992%", "99.990%", "+0.0016%", "99.995%", "99.993%", "+0.0011%", "Optimal Fit (No Overfitting)"],
        ["Random Forest", "100.00%", "99.990%", "+0.0096%", "100.00%", "99.993%", "+0.0066%", "Optimal Fit (No Overfitting)"],
        ["XGBoost", "99.998%", "99.990%", "+0.0076%", "99.999%", "99.993%", "+0.0052%", "Optimal Fit (No Overfitting)"],
        ["LSTM (Neural)", "99.486%", "99.875%", "-0.3887%", "99.647%", "99.914%", "-0.2674%", "Optimal Fit (No Overfitting)"],
        ["Logistic Regression", "98.852%", "98.904%", "-0.0522%", "99.211%", "99.247%", "-0.0360%", "Optimal Fit (No Overfitting)"],
    ]
    add_styled_table(s13, Inches(0.8), Inches(1.6), Inches(11.7), Inches(2.6), headers_s13, rows_s13,
                     col_widths=[Inches(2.1), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2), Inches(2.4)])

    # Embedded Overfitting Plot
    overfit_img = os.path.join(VIS_DIR, "overfitting_train_vs_test.png")
    if os.path.exists(overfit_img):
        add_card(s13, Inches(0.8), Inches(4.4), Inches(7.0), Inches(2.7))
        s13.shapes.add_picture(overfit_img, Inches(1.0), Inches(4.5), Inches(6.6), Inches(2.5))

    # Generalization sub-test card
    add_card(s13, Inches(8.1), Inches(4.4), Inches(4.4), Inches(2.7))
    s13_gt = s13.shapes.add_textbox(Inches(8.3), Inches(4.5), Inches(4.0), Inches(0.4))
    s13_gt.text_frame.paragraphs[0].text = "Blinded Zero-Day Test (NTP Held Out)"
    s13_gt.text_frame.paragraphs[0].font.size = Pt(13)
    s13_gt.text_frame.paragraphs[0].font.bold = True
    s13_gt.text_frame.paragraphs[0].font.color.rgb = COLOR_AMBER

    b_gen = [
        ("Decision Tree", "99.97% Accuracy | 100.0% Recall"),
        ("XGBoost", "99.96% Accuracy | 99.99% Recall"),
        ("Random Forest", "99.98% Accuracy | 99.98% Recall"),
        ("Conclusion", "Proves zero-day generalization against completely unseen attack classes."),
    ]
    add_bullet_list(s13, Inches(8.3), Inches(5.0), Inches(4.0), Inches(1.9), b_gen, font_size=10, space_after=4)

    # =========================================================================
    # SLIDE 14: Accuracy vs. Latency Trade-Off (Phase 5)
    # =========================================================================
    s14 = create_base_slide(prs, "SDN Deployment Trade-Off: Accuracy vs. Latency", "PHASE 5: PRODUCTION SELECTION")

    acc_lat_img = os.path.join(VIS_DIR, "accuracy_vs_latency.png")
    if os.path.exists(acc_lat_img):
        add_card(s14, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2))
        s14.shapes.add_picture(acc_lat_img, Inches(1.0), Inches(1.8), Inches(7.1), Inches(4.8))

    add_card(s14, Inches(8.6), Inches(1.6), Inches(3.9), Inches(5.2))
    s14_rt = s14.shapes.add_textbox(Inches(8.8), Inches(1.8), Inches(3.5), Inches(0.5))
    s14_rt.text_frame.paragraphs[0].text = "Why Latency Dictates Selection"
    s14_rt.text_frame.paragraphs[0].font.size = Pt(16)
    s14_rt.text_frame.paragraphs[0].font.bold = True
    s14_rt.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    lat_bullets = [
        ("The 5.0 ms SDN Boundary", "Ryu controller flow-table updates must complete before OpenFlow packet buffers overflow."),
        ("Decision Tree Superiority", "0.142 ms latency provides a 35x safety buffer under line-rate traffic spikes."),
        ("XGBoost Viability", "0.525 ms latency also passes the SLA with high robustness."),
        ("Ensemble & LSTM Overhead", "Random Forest (36.87 ms) and LSTM (91.64 ms) fail real-time SDN SLAs despite high accuracy."),
        ("Winning Model", "Decision Tree chosen as best_sdn_model.joblib for production deployment."),
    ]
    add_bullet_list(s14, Inches(8.8), Inches(2.4), Inches(3.5), Inches(4.2), lat_bullets, font_size=11, space_after=10)

    # =========================================================================
    # SLIDE 15: Packaging & Ryu Controller Integration (Phase 5)
    # =========================================================================
    s15 = create_base_slide(prs, "Production Packaging & Ryu Controller Integration", "PHASE 5: DEPLOYMENT & SUMMARY")

    add_card(s15, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    s15_t1 = s15.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s15_t1.text_frame.paragraphs[0].text = "predict.py Module Verification"
    s15_t1.text_frame.paragraphs[0].font.size = Pt(17)
    s15_t1.text_frame.paragraphs[0].font.bold = True
    s15_t1.text_frame.paragraphs[0].font.color.rgb = COLOR_CYAN

    pred_bullets = [
        ("Callable API", "predict_packet(packet_data) accepts dicts, numpy arrays, or pandas Series."),
        ("In-Memory Caching", "Pre-loads best_sdn_model.joblib and scaler.joblib once on controller launch."),
        ("Measured Average Latency", "0.578 ms / packet (500 iterations benchmarked)."),
        ("99th Percentile Latency", "0.649 ms / packet (Zero latency spikes observed)."),
        ("SLA Compliance Status", "PASSED: Well below the 5.0 ms threshold."),
        ("Response Contract", "{'is_ddos': True, 'label': 'ATTACK', 'confidence': 1.0, 'latency_ms': 0.568, 'action': 'DROP'}"),
    ]
    add_bullet_list(s15, Inches(1.1), Inches(2.4), Inches(5.0), Inches(4.2), pred_bullets, font_size=11, space_after=10)

    add_card(s15, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    s15_t2 = s15.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.0), Inches(0.5))
    s15_t2.text_frame.paragraphs[0].text = "Ryu Controller OpenFlow Mitigation"
    s15_t2.text_frame.paragraphs[0].font.size = Pt(17)
    s15_t2.text_frame.paragraphs[0].font.bold = True
    s15_t2.text_frame.paragraphs[0].font.color.rgb = COLOR_EMERALD

    mit_bullets = [
        ("Event Hooking", "Integrated into EventOFPFlowStatsReply and EventOFPPacketIn handlers."),
        ("Autonomous Drop Rule", "Installs OFPFlowMod with OFPIT_APPLY_ACTIONS (empty action list = drop)."),
        ("Priority Override", "High priority (1000) overrides normal forwarding for the offending flow match."),
        ("Hard Timeout Expiry", "Sets 60s hard timeout to prevent stale flow table rule accumulation."),
        ("Deliverable State", "All code pushed to GitHub repo botvecna47/SDN-Based-DDoS-Mitigation at mlbranch."),
    ]
    add_bullet_list(s15, Inches(7.1), Inches(2.4), Inches(5.0), Inches(4.2), mit_bullets, font_size=11, space_after=10)

    # Save presentation
    prs.save(OUTPUT_PPTX)
    print(f"Successfully generated 15-slide presentation: {OUTPUT_PPTX}")


if __name__ == "__main__":
    build_deck()

