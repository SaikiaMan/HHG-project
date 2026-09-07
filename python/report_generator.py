"""
HHG Media Integrity - Visual Report Generator
Generates a standalone, polished HTML evaluation report (results/latest_result.html)
displaying side-by-side comparison of the input face and the matching online source,
along with biometric similarity scores and blockchain notarization status.
"""

import base64
import html
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional


def image_to_data_uri(image_path: Optional[Path]) -> str:
    """Encodes an image file to a base64 data URI for standalone HTML embedding."""
    if not image_path:
        return ""
    p = Path(image_path)
    if not p.exists() or not p.is_file():
        return ""
    mime_type, _ = mimetypes.guess_type(str(p))
    if not mime_type:
        mime_type = "image/jpeg"
    try:
        data = p.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""


def generate_html_report(
    data: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates results/latest_result.html with side-by-side comparison and verification badges.
    """
    project_root = Path(__file__).resolve().parent.parent
    if output_path is None:
        output_path = project_root / "results" / "latest_result.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    input_img_path = Path(data.get("input_image", "")) if data.get("input_image") else None
    cand_img_path = Path(data.get("candidate_image", "")) if data.get("candidate_image") else None

    input_b64 = image_to_data_uri(input_img_path)
    cand_b64 = image_to_data_uri(cand_img_path)

    similarity = data.get("similarity")
    sim_str = f"{similarity:.4f}" if similarity is not None else "N/A"
    is_match = data.get("is_match", False)
    threshold = data.get("threshold", 0.50)

    source = html.escape(str(data.get("source") or "Web"))
    url = str(data.get("url") or "#")
    url_escaped = html.escape(url)
    title = html.escape(str(data.get("title") or "Candidate Match"))
    sha256 = html.escape(str(data.get("sha256") or "N/A"))
    blockchain_status = str(data.get("blockchain_status") or "NOT REGISTERED")
    tx_hash = data.get("tx_hash")
    block_num = data.get("block_number")
    contract_addr = data.get("contract_address")
    verdict = html.escape(str(data.get("verdict") or "EVALUATION COMPLETE"))

    sim_percent = min(100, max(0, int((similarity if similarity is not None else 0) * 100)))

    # Status color coding
    if is_match and "VERIFIED" in blockchain_status:
        accent_color = "#10b981"  # Emerald
        status_badge = '<span class="badge badge-success">&#10003; AUTHENTIC / VERIFIED</span>'
    elif is_match:
        accent_color = "#3b82f6"  # Blue
        status_badge = '<span class="badge badge-info">&#10003; PERSON FOUND ONLINE</span>'
    elif "SUSPICIOUS" in verdict or (similarity is not None and similarity < threshold):
        accent_color = "#ef4444"  # Red
        status_badge = '<span class="badge badge-danger">&#128680; SUSPICIOUS / POSSIBLE DEEPFAKE</span>'
    else:
        accent_color = "#f59e0b"  # Amber
        status_badge = '<span class="badge badge-warning">&#9888; UNVERIFIED</span>'

    blockchain_badge = (
        '<span class="badge badge-success">&#10003; VERIFIED ON-CHAIN</span>'
        if "VERIFIED" in blockchain_status
        else '<span class="badge badge-warning">&#10007; NOT REGISTERED</span>'
    )

    match_badge = (
        '<span class="badge badge-success">&#10003; MATCH (&ge; 0.50)</span>'
        if is_match
        else '<span class="badge badge-danger">&#10007; MISMATCH</span>'
    )

    tx_section = ""
    if tx_hash:
        tx_section = f"""
        <div class="meta-row">
            <span class="meta-label">Tx Hash:</span>
            <span class="meta-val font-mono">{html.escape(str(tx_hash))}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Block #:</span>
            <span class="meta-val">{block_num}</span>
        </div>
        """

    contract_section = ""
    if contract_addr:
        contract_section = f"""
        <div class="meta-row">
            <span class="meta-label">Contract:</span>
            <span class="meta-val font-mono">{html.escape(str(contract_addr))}</span>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HHG Media Integrity - Verification Result</title>
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: {accent_color};
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 32px 16px;
            display: flex;
            justify-content: center;
            line-height: 1.5;
        }}
        .container {{
            max-width: 960px;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 28px;
        }}
        .header h1 {{
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
            color: #fff;
        }}
        .header p {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .verdict-banner {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 2px solid var(--accent);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .verdict-text h2 {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 4px;
        }}
        .verdict-text p {{
            color: var(--text-muted);
            font-size: 13px;
        }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-success {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
        .badge-info {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }}

        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 28px;
        }}
        @media (max-width: 768px) {{
            .comparison-grid {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
        }}
        .card-header {{
            padding: 14px 18px;
            background: rgba(15, 23, 42, 0.6);
            border-bottom: 1px solid var(--card-border);
            font-weight: 600;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .img-wrapper {{
            width: 100%;
            height: 320px;
            background: #090d16;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 12px;
        }}
        .img-wrapper img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 6px;
        }}
        .card-body {{
            padding: 16px 18px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .meta-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            gap: 12px;
        }}
        .meta-label {{
            color: var(--text-muted);
            white-space: nowrap;
        }}
        .meta-val {{
            color: var(--text-main);
            text-align: right;
            word-break: break-all;
        }}
        .font-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 12px;
        }}
        .source-link {{
            display: inline-block;
            color: #60a5fa;
            text-decoration: none;
            font-weight: 500;
            word-break: break-all;
        }}
        .source-link:hover {{
            text-decoration: underline;
        }}

        .metrics-panel {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 24px;
        }}
        .metrics-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .progress-bar-container {{
            background: #0f172a;
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
            margin: 8px 0 16px 0;
            border: 1px solid #334155;
        }}
        .progress-bar {{
            height: 100%;
            background: var(--accent);
            width: {sim_percent}%;
            transition: width 0.4s ease;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 32px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>HHG MEDIA INTEGRITY &amp; PROVENANCE</h1>
            <p>Biometric Visual Provenance &amp; Cryptographic Blockchain Verification</p>
        </div>

        <div class="verdict-banner">
            <div class="verdict-text">
                <h2>{verdict}</h2>
                <p>Provenance verified via Google Lens &amp; InsightFace biometrics</p>
            </div>
            <div>{status_badge}</div>
        </div>

        <div class="comparison-grid">
            <!-- Card 1: Input Face -->
            <div class="card">
                <div class="card-header">
                    <span>INPUT TARGET FACE</span>
                    <span class="badge badge-info">Input Image</span>
                </div>
                <div class="img-wrapper">
                    {"<img src='" + input_b64 + "' alt='Input Face'>" if input_b64 else "<p style='color:#64748b;'>Image not available</p>"}
                </div>
                <div class="card-body">
                    <div class="meta-row">
                        <span class="meta-label">File:</span>
                        <span class="meta-val font-mono">{input_img_path.name if input_img_path else "N/A"}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">SHA-256:</span>
                        <span class="meta-val font-mono">{sha256[:20]}...{sha256[-8:] if len(sha256) > 28 else ''}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Blockchain:</span>
                        <span class="meta-val">{blockchain_badge}</span>
                    </div>
                </div>
            </div>

            <!-- Card 2: Best Online Match -->
            <div class="card">
                <div class="card-header">
                    <span>MATCHING ONLINE SOURCE</span>
                    <span class="badge badge-success">{source}</span>
                </div>
                <div class="img-wrapper">
                    {"<img src='" + cand_b64 + "' alt='Online Match'>" if cand_b64 else "<p style='color:#64748b;'>Candidate image not available</p>"}
                </div>
                <div class="card-body">
                    <div class="meta-row">
                        <span class="meta-label">Source Platform:</span>
                        <span class="meta-val"><strong>{source}</strong></span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Post Title:</span>
                        <span class="meta-val">{title[:50]}...</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Web URL:</span>
                        <span class="meta-val">
                            <a class="source-link" href="{url_escaped}" target="_blank" rel="noopener noreferrer">
                                {url_escaped[:42]}...
                            </a>
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Metrics & Verification Details -->
        <div class="metrics-panel">
            <div class="metrics-title">
                <span>Biometric Face Verification Analysis</span>
                <div style="margin-left: auto;">{match_badge}</div>
            </div>
            <div class="meta-row">
                <span class="meta-label">Cosine Similarity:</span>
                <span class="meta-val font-mono"><strong>{sim_str}</strong> (Threshold: &ge; {threshold:.2f})</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar"></div>
            </div>
            <p style="font-size: 13px; color: var(--text-muted);">
                InsightFace buffalo_l deep embedding comparison between input face and online candidate.
                Scores &ge; 0.50 indicate the same person across different scenes, lighting, or angles.
            </p>
        </div>

        <div class="metrics-panel">
            <div class="metrics-title">
                <span>Cryptographic Blockchain Notarization</span>
                <div style="margin-left: auto;">{blockchain_badge}</div>
            </div>
            <div class="meta-row">
                <span class="meta-label">Full SHA-256:</span>
                <span class="meta-val font-mono">{sha256}</span>
            </div>
            {contract_section}
            {tx_section}
            <p style="font-size: 13px; color: var(--text-muted); margin-top: 10px;">
                Blockchain verification confirms that the exact file matches a previously notarized cryptographic fingerprint on the smart contract.
            </p>
        </div>

        <div class="footer">
            HHG Media Integrity System &bull; Live Hackathon Demonstration
        </div>
    </div>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")
    return output_path
