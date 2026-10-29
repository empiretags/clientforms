import streamlit as st
from datetime import date
from pypdf import PdfReader, PdfWriter
import io
import base64
import requests
import json
import zipfile

# ============ CONFIG ============
XAI_API_KEY = "xai-5NEzWhbJ4lMdXHD9EBNK3ykphmoBs7ZnGUqMdvDwK5YEAsQw3FVKLMEjf7neWFytrXCj56IYvg8XBHG4"
# =================================

st.set_page_config(page_title="Empire State Tags", page_icon="🏷️", layout="centered")

if "step" not in st.session_state:
    st.session_state.step = 1
if "form_data" not in st.session_state:
    st.session_state.form_data = {}

st.markdown("""
<style>
    .stApp { background-color: #e8f4fc; }
    h1, h2, h3 { color: #0a2f5c !important; font-weight: 700; }
    label, .stMarkdown p { color: #0a2f5c !important; font-size: 1.05rem !important; font-weight: 600; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background: white !important; color: #0a2f5c !important; font-size: 1.1rem !important;
        border: 2px solid #0a2f5c !important; border-radius: 8px;
    }
    .stButton > button {
        background-color: #0a2f5c !important; color: white !important;
        border-radius: 12px; width: 100%; font-weight: 700; font-size: 1.15rem !important;
        padding: 0.9rem !important; border: none !important; min-height: 52px;
    }
    .stButton > button * { color: white !important; }
    .stButton > button:hover { background-color: #1a4a8a !important; }
    .block-container { border: 3px solid #7eb6e0; border-radius: 18px; padding: 24px; background: #f7fbff; }
    .step-badge { background: #0a2f5c; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 700; display: inline-block; margin-bottom: 12px; }
    .stWarning, .stWarning p, .stWarning div, .stWarning span {
        color: #000000 !important;
        background-color: #fff3cd !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    .stError p, .stError div, .stError span, .stError li, .stMarkdown p {
        color: #000000 !important;
    }
    .flag-box {
        background: #ffdddd;
        border: 3px solid #cc0000;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        color: #000000 !important;
        font-weight: 700;
        font-size: 1.25rem;
        line-height: 1.5;
    }
    @media (max-width: 600px) {
        .flag-box { font-size: 1.35rem; padding: 20px; }
    }
</style>
""", unsafe_allow_html=True)

st.image("empire_state_tags_logo.png", width=220)
st.title("Client Data Extraction")
st.caption("Empire State Tags  •  Virginia Title & Registration  •  Internal Use Only")

def image_to_base64(file):
    if file is None:
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file.getvalue()))
        img = img.convert("RGB")
        max_size = 1600
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return base64.b64encode(file.getvalue()).decode()

def check_image_quality(file):
    """Warn if image is too small or very dark."""
    if file is None:
        return None
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(io.BytesIO(file.getvalue()))
        w, h = img.size
        warnings = []
        if max(w, h) < 1000:
            warnings.append(f"too small ({w}x{h}) — re-take closer")
        # Check brightness without numpy
        gray = img.convert("L")
        pixels = list(gray.getdata())
        avg = sum(pixels) / len(pixels) if pixels else 128
        if avg < 60:
            warnings.append("very dark — re-take with better lighting")
        if warnings:
            return "; ".join(warnings)
    except:
        pass
    return None
    if file is None:
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file.getvalue()))
        img = img.convert("RGB")
        max_size = 1600
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return base64.b64encode(file.getvalue()).decode()

def pdf_to_images_b64(pdf_file):
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(pdf_file.getvalue(), dpi=100)
        b64_list = []
        for page in pages:
            buf = io.BytesIO()
            page.save(buf, format="JPEG", quality=70)
            b64_list.append(base64.b64encode(buf.getvalue()).decode())
        return b64_list
    except Exception as e:
        st.warning(f"Could not convert PDF: {e}")
        return []

def safe_int(val, default=0):
    try:
        if val is None or str(val).strip() == "":
            return default
        return int(float(str(val).replace(",", "").replace("$", "").strip()))
    except:
        return default

def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(str(val).replace(",", "").replace("$", "").strip())
    except:
        return default

def extract_address_only(images_b64):
    """Focused pass that only looks for the address on the ID."""
    if not images_b64:
        return ""
    prompt = (
        "You are looking at a customer ID, driver's license, passport, or green card. "
        "Extract ONLY the complete residential address exactly as printed on the document. "
        "Include street number and name, city, state, and zip code. "
        "Return the address as a single line of plain text. "
        "If you cannot read an address, return the word NONE."
    )
    content = [{"type": "input_text", "text": prompt}]
    for b64 in images_b64[:2]:
        if b64:
            content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "high"})
    try:
        resp = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-4.7", "input": [{"role": "user", "content": content}], "max_output_tokens": 150},
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        result = c.get("text", "").strip()
                        if result and result.upper() != "NONE":
                            return result
    except Exception as e:
        st.warning(f"Address pass failed: {e}")
    return ""

def fix_name_order(name):
    """Convert LAST, FIRST MIDDLE to First Middle Last."""
    if not name or "," not in name:
        return name
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}".title()
    return name

def extract_with_grok(images_b64):
    if not images_b64:
        st.warning("No images to process.")
        return {}
    st.info(f"Sending {len(images_b64)} image(s) for extraction...")
    prompt = (
        "You are extracting data for a Virginia vehicle title transfer. "
        "Carefully examine EVERY uploaded image (ID, bill of sale pages, title front/back, reassignment). "
        "The person on the Customer ID / Passport / Green Card is ALWAYS the buyer. "
        "ALWAYS extract the complete residential address exactly as printed on the ID or license (street, city, state, zip). "
        "Put the full address in the buyer_address field. "
        "Return ONLY a JSON object with these keys. Use empty string ONLY if the information is truly not visible or unreadable: "
        "buyer_name, buyer_address, co_owner_name, year, make, model, vin, title_number, "
        "body_type, color, sale_date, price, odometer, seller_name, seller_street, seller_city, seller_state, seller_zip, seller_address, lienholder, "
        "title_already_in_buyer_name, seller_from_title_back, insurance_provider, ssn, unreadable_fields. "
        "Rules: "
        "- Use FULL official make and model names (expand abbreviations). "
        "- Extract VIN exactly as printed. "
        "- Extract the previous title number from the title document if visible. "
        "- Extract the SELLER name and FULL address (street, city, state, zip) from BOTH the title (owner section or title back) AND the bill of sale. Prefer the bill of sale if both exist and differ. Fill seller_name, seller_street, seller_city, seller_state, seller_zip. "
        "- Extract body type EXACTLY as printed on the title (e.g. SUBN, 4D, SDN). Do not change it to SUV or sedan. "
        "- Color codes: BL or BLU = Blue, BK or BLK = Black, WH or WHT = White, RD or RED = Red, "
        "GR or GRN = Green, GY or GRY = Gray, SL or SIL = Silver, TN or TAN = Tan, "
        "BG or BGE = Beige, OR or ORG = Orange, YL or YEL = Yellow, BR or BRN = Brown, "
        "GD or GLD = Gold, PR or PUR = Purple. Always expand the code to the full color name. "
        "- Extract the title/document number from the title (not the VIN). "
        "- Convert buyer name from LAST, FIRST MIDDLE format to First Middle Last. "
        "- Extract sale date and price if present on bill of sale. "
        "- Extract odometer if visible. "
        "- If the buyer is registering under a business name (LLC, Inc, Corp, or company name visible on the ID, documents, or letter of formation), use the business name as buyer_name. "
        "- List any blurry or cut-off areas in unreadable_fields. "
        "- Phone number is rarely on documents — leave it empty unless clearly visible. "
        "Do not invent data. Be thorough."
    )
    content = [{"type": "input_text", "text": prompt}]
    for b64 in images_b64:
        if b64:
            content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "high"})
    try:
        resp = requests.post(
            "https://api.x.ai/v1/responses",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-4.7", "input": [{"role": "user", "content": content}], "max_output_tokens": 2500},
            timeout=180
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        text = c.get("text", "")
                        break
        with st.expander("Raw extraction response (debug)", expanded=True):
            st.code(text[:1500] if text else "(empty response)")
            st.caption(f"Status: {resp.status_code} | Images sent: {len(images_b64)}")
        if not text or not text.strip():
            st.error("Extraction returned no text. Try clearer photos.")
            return {}
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0]
        clean = clean.strip()
        try:
            result = json.loads(clean)
            filled = sum(1 for v in result.values() if v and str(v).strip())
            st.success(f"Extracted {filled} fields")
            return result
        except json.JSONDecodeError as je:
            st.error(f"Could not parse JSON: {je}")
            st.code(clean[:800])
            return {}
    except Exception as e:
        st.error(f"Extraction failed: {type(e).__name__}: {e}")
        try:
            st.code(resp.text[:600])
        except:
            pass
        return {}

def fill_pdf(template_path, field_values):
    from pypdf.generic import NameObject, BooleanObject
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, field_values)
        except:
            pass
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update({NameObject("/NeedAppearances"): BooleanObject(True)})
    # Mark radio buttons by setting widget appearance
    reg = field_values.get("reg_period", "1 year") if field_values else "1 year"
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot_ref in annots:
            try:
                annot = annot_ref.get_object()
                nm = str(annot.get("/NM", ""))
                # Low speed / logging = No
                if "subform[2].RadioButtonList" in nm and "#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/0")
                # Electronic title = No only (force Yes off)
                if "owner_info[0].RadioButtonList[1].#field[1]" in nm:
                    annot[NameObject("/AS")] = NameObject("/1")
                elif "owner_info[0].RadioButtonList[1].#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/Off")
                # Title and Registration (or Title Only)
                elif "owner_info[0].RadioButtonList[0].#field[1]" in nm and field_values.get("application_type") != "Title Only":
                    annot[NameObject("/AS")] = NameObject("/1")
                elif "owner_info[0].RadioButtonList[0].#field[0]" in nm and field_values.get("application_type") == "Title Only":
                    annot[NameObject("/AS")] = NameObject("/0")
                # Individual ownership
                elif "owner_info[0].RadioButtonList[2].#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/0")
                # Lien = No
                elif "LIEN" in nm and "#field[1]" in nm:
                    annot[NameObject("/AS")] = NameObject("/1")
                # Locality owned = No
                elif "local-owned" in nm and "#field[1]" in nm:
                    annot[NameObject("/AS")] = NameObject("/1")
                # Used vehicle
                elif "SOURCE_OWNERSHIP" in nm and "#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/0")
                # Odometer statement based on Step 2
                status = field_values.get("odometer_status") or "Actual mileage"
                if "odometer_statement" in nm:
                    if status == "Actual mileage" and "#field[0]" in nm:
                        annot[NameObject("/AS")] = NameObject("/0")
                    elif "discrepancy" in status and "#field[1]" in nm:
                        annot[NameObject("/AS")] = NameObject("/1")
                    elif "excess" in status and "#field[2]" in nm:
                        annot[NameObject("/AS")] = NameObject("/2")
                    elif "Exempt" in status and "#field[3]" in nm:
                        annot[NameObject("/AS")] = NameObject("/3")
                # Personal Use
                elif "PERSONAL_PROPERTY" in nm and "#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/0")
                # Registration period based on employee choice
                elif "RadioButtonList[0].ONE[0]" in nm and reg == "1 year":
                    annot[NameObject("/AS")] = NameObject("/3")
                elif "RadioButtonList[0].TWO[0]" in nm and reg == "2 years":
                    annot[NameObject("/AS")] = NameObject("/2")
                elif "RadioButtonList[0].THREE[0]" in nm and reg == "3 years":
                    annot[NameObject("/AS")] = NameObject("/1")
                # Never mark Transfer
                elif "TRANSFER" in nm:
                    annot[NameObject("/AS")] = NameObject("/Off")
                # Registration type = Private
                elif "RegInfo[0].RadioButtonList[1].#field[2]" in nm:
                    annot[NameObject("/AS")] = NameObject("/2")
                # For Hire off
                elif "RegInfo[0].RadioButtonList[1].#field[0]" in nm or ("FR_HIRE" in nm and "#field[0]" in nm):
                    annot[NameObject("/AS")] = NameObject("/Off")
                # Insurance certification checkbox
                elif "INSURANCE[0].#field[1]" in nm:
                    annot[NameObject("/AS")] = NameObject("/1")
                # Title and Registration (or Title Only based on selection)
                elif "owner_info[0].RadioButtonList[1].#field[0]" in nm:
                    annot[NameObject("/AS")] = NameObject("/0")  # Title and Registration
                elif "owner_info[0].RadioButtonList[1].#field[1]" in nm and field_values.get("application_type") == "Title Only":
                    annot[NameObject("/AS")] = NameObject("/1")
                # Registration period based on employee choice
                elif "RadioButtonList[0].ONE[0]" in nm and reg == "1 year":
                    annot[NameObject("/AS")] = NameObject("/3")
                elif "RadioButtonList[0].TWO[0]" in nm and reg == "2 years":
                    annot[NameObject("/AS")] = NameObject("/2")
                elif "RadioButtonList[0].THREE[0]" in nm and reg == "3 years":
                    annot[NameObject("/AS")] = NameObject("/1")
                elif "TRANSFER" in nm:
                    annot[NameObject("/AS")] = NameObject("/Off")
                # Odometer statement based on Step 2
                status = field_values.get("odometer_status") or "Actual mileage"
                if "odometer_statement" in nm:
                    if status == "Actual mileage" and "#field[0]" in nm:
                        annot[NameObject("/AS")] = NameObject("/0")
                    elif "discrepancy" in status and "#field[1]" in nm:
                        annot[NameObject("/AS")] = NameObject("/1")
                    elif "excess" in status and "#field[2]" in nm:
                        annot[NameObject("/AS")] = NameObject("/2")
                    elif "Exempt" in status and "#field[3]" in nm:
                        annot[NameObject("/AS")] = NameObject("/3")
            except:
                pass
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    # Draw tax relief No X marks on page 2
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica-Bold", 8)
        # Approximate No-box positions for a-d (adjust if needed)
        for y in (710, 698, 686, 674):
            c.drawString(530, y, "X")
        c.save()
        packet.seek(0)
        overlay = PdfReader(packet)
        final = PdfWriter()
        base = PdfReader(buf)
        final.append(base)
        final.pages[1].merge_page(overlay.pages[0])
        out = io.BytesIO()
        final.write(out)
        out.seek(0)
        return out
    except:
        return buf

# ==================== STEP 1 ====================
if st.session_state.step == 1:
    st.markdown('<div class="step-badge">Step 1 of 3 — Upload Documents</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#0a2f5c; color:white; padding:18px; border-radius:12px; font-size:1.05rem; line-height:1.55; margin-bottom:18px;">
<strong style="color:white;">Forms Generated by This Tool</strong><br><br>
• VSA 17A — Application for Certificate of Title and Registration<br>
• VSA 70 — Power of Attorney (owner information completed)<br>
• Vehicle Price Certification<br>
• New York Bill of Sale (optional, upon request)<br><br>
<strong>Instructions</strong><br>
1. Upload clear, well-lit photos or a PDF of the Bill of Sale.<br>
2. A Customer ID, Passport, or Green Card is required.<br>
3. Title, Reassignment, and Business Letter of Formation are optional.<br>
4. Select <strong>Extract & Continue</strong> to review the information and generate the completed forms.
</div>
""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        bill_pages = st.file_uploader("Bill of Sale (photos or PDF — all pages)", type=["jpg","jpeg","png","pdf"], accept_multiple_files=True)
        id_photo = st.file_uploader("Customer ID / Passport / Green Card (required)", type=["jpg","jpeg","png"])
    with col2:
        title_front = st.file_uploader("Title – Front", type=["jpg","jpeg","png"])
        title_back = st.file_uploader("Title – Back (optional)", type=["jpg","jpeg","png"])
        reassignment = st.file_uploader("Reassignment Form (optional)", type=["jpg","jpeg","png"])
        business_letter = st.file_uploader("Business Letter of Formation (optional)", type=["jpg","jpeg","png","pdf"])
        insurance_card = st.file_uploader("Insurance Card (optional)", type=["jpg","jpeg","png","pdf"])
        lien_release = st.file_uploader("Lien Release (optional)", type=["jpg","jpeg","png","pdf"])

    if st.button("Extract & Continue", type="primary"):
        if not id_photo:
            st.error("Customer ID, Passport, or Green Card is required.")
        else:
            # Photo quality warnings
            for label, f in [("ID", id_photo), ("Title Front", title_front)]:
                if f:
                    warn = check_image_quality(f)
                    if warn:
                        st.warning(f"{label}: {warn}")
            files = []
            if bill_pages:
                files.extend(bill_pages)
            for f in [id_photo, title_front, title_back, reassignment, business_letter, insurance_card, lien_release]:
                if f:
                    files.append(f)
            images = []
            for f in files:
                if f.type == "application/pdf" or (f.name and f.name.lower().endswith(".pdf")):
                    images.extend(pdf_to_images_b64(f))
                else:
                    b64 = image_to_base64(f)
                    if b64:
                        images.append(b64)
            progress = st.progress(0, text="Preparing images...")
            progress.progress(20, text="Sending documents — this usually takes 1–3 minutes...")
            extracted = extract_with_grok(images)
            progress.progress(75, text="Reading results...")
            # Only run second address pass if the first one missed it
            if not extracted.get("buyer_address") or len(str(extracted.get("buyer_address"))) < 8:
                progress.progress(85, text="Looking for address...")
                addr = extract_address_only(images[:2])
                if addr and len(addr) > 5:
                    extracted["buyer_address"] = addr
                    st.info(f"Address found: {addr}")
            progress.progress(100, text="Done — opening review page")
            st.session_state.form_data = extracted
            # Store original high-quality images for preview
            st.session_state.id_photo_bytes = id_photo.getvalue() if id_photo else None
            st.session_state.bill_photos = [f.getvalue() for f in bill_pages] if bill_pages else []
            st.session_state.title_front_bytes = title_front.getvalue() if title_front else None
            st.session_state.title_back_bytes = title_back.getvalue() if title_back else None
            st.session_state.step = 2
            st.rerun()

# ==================== STEP 2 ====================
elif st.session_state.step == 2:
    st.markdown('<div class="step-badge">Step 2 of 3 — Review & Correct</div>', unsafe_allow_html=True)
    st.info("Review all extracted information carefully. The individual shown on the identification document is the applicant. Correct any errors or missing details before continuing.")

    # Remove the single expander — photos will appear next to their fields below
    d = st.session_state.form_data or {}

    flags = []
    if not d.get("buyer_name"):
        flags.append("Buyer name not found — check that the ID photo is clear and fully visible")
    if not d.get("buyer_address") and not d.get("street"):
        flags.append("Address not found on ID — re-take the photo or enter it manually")
    if not d.get("phone"):
        flags.append("Phone missing — type it manually (usually not on ID)")
    if not d.get("vin") or len(str(d.get("vin") or "").strip()) < 17:
        flags.append("VIN not found or incomplete — check the title photo")
    if d.get("unreadable_fields"):
        flags.append(f"Could not read: {d.get('unreadable_fields')} — photo may be too dark or blurry")

    if flags:
        flag_html = "<div class='flag-box'><strong>Please review:</strong><br>" + "<br>".join(f"• {f}" for f in flags) + "</div>"
        st.markdown(flag_html, unsafe_allow_html=True)
    else:
        st.success("No major problems flagged.")

    with st.form("review"):
        # Buyer section with ID photo
        if st.session_state.get("id_photo_bytes"):
            st.image(st.session_state.id_photo_bytes, caption="Customer ID", use_container_width=True)
        buyer_name = st.text_input("Buyer / Applicant Full Legal Name", value=fix_name_order(d.get("buyer_name") or ""))
        if not d.get("buyer_name"):
            st.markdown("<span style='color:#cc0000;font-weight:700;'>Name is required</span>", unsafe_allow_html=True)

        st.markdown("**Address (from ID)**")
        full_addr = d.get("buyer_address") or ""
        street_val = d.get("street") or ""
        city_val = d.get("city") or ""
        state_val = d.get("state") or ""
        zip_val = d.get("zip") or ""
        if full_addr and not street_val:
            # Better address split
            addr = full_addr.replace("\n", ", ")
            parts = [p.strip() for p in addr.split(",") if p.strip()]
            if len(parts) >= 3:
                street_val = parts[0]
                city_val = parts[1]
                rest = parts[2].replace("  ", " ").split()
                if rest:
                    state_val = rest[0]
                if len(rest) > 1:
                    zip_val = rest[-1]
            elif len(parts) == 2:
                street_val = parts[0]
                rest = parts[1].split()
                if len(rest) >= 3:
                    zip_val = rest[-1]
                    state_val = rest[-2]
                    city_val = " ".join(rest[:-2])
            elif len(parts) == 1:
                street_val = parts[0]
        street = st.text_input("Street Address", value=street_val)
        if not street_val:
            st.markdown("<span style='color:#cc0000;font-weight:700;'>Street address is required</span>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            city = st.text_input("City", value=city_val)
        with c2:
            state = st.text_input("State", value=state_val)
        with c3:
            zip_code = st.text_input("Zip", value=zip_val)
        # Address confirmation
        if street_val or city_val:
            full_display = f"{street_val}, {city_val}, {state_val} {zip_code}".strip(", ")
            st.info(f"**Confirm this address:** {full_display}")
            st.caption("Check against the ID photo above. Correct any part that looks wrong.")

        # Vehicle section with title photos
        st.markdown("---")
        if st.session_state.get("title_front_bytes"):
            st.image(st.session_state.title_front_bytes, caption="Title Front", use_container_width=True)
        if st.session_state.get("title_back_bytes"):
            st.image(st.session_state.title_back_bytes, caption="Title Back", use_container_width=True)
        year = st.text_input("Year", value=d.get("year") or "")
        make = st.text_input("Make", value=d.get("make") or "")
        if not d.get("make"):
            st.markdown("<span style='color:#cc0000;font-weight:700;'>Make is required</span>", unsafe_allow_html=True)
        model = st.text_input("Model", value=d.get("model") or "")
        if not d.get("model"):
            st.markdown("<span style='color:#cc0000;font-weight:700;'>Model is required</span>", unsafe_allow_html=True)
        vin = st.text_input("VIN", value=d.get("vin") or "")
        if not d.get("vin") or len(str(d.get("vin") or "")) < 11:
            st.markdown("<span style='color:#cc0000;font-weight:700;'>VIN is required</span>", unsafe_allow_html=True)
        body_type = st.text_input("Body Type", value=d.get("body_type") or "")
        color = st.text_input("Color", value=d.get("color") or "")
        fuel_default = "Electric" if "tesla" in str(d.get("make") or "").lower() else "Gas"
        fuel_type = st.selectbox("Fuel Type", ["Gas", "Diesel", "Electric", "Other"], index=["Gas","Diesel","Electric","Other"].index(fuel_default))

        # Sale section with bill of sale
        st.markdown("---")
        if st.session_state.get("bill_photos"):
            for i, b in enumerate(st.session_state.bill_photos):
                st.image(b, caption=f"Bill of Sale page {i+1}", use_container_width=True)
        phone = st.text_input("Phone Number (type manually if missing)", value=d.get("phone") or "")
        email = st.text_input("Email (optional)", value=d.get("email") or "")
        co_owner_name = st.text_input("Co-owner Name", value=d.get("co_owner_name") or "")
        title_number = st.text_input("Title Number", value=d.get("title_number") or "")
        sale_date = st.text_input("Sale Date", value=d.get("sale_date") or str(date.today()))
        price = st.number_input("Purchase Price ($)", min_value=0.0, value=safe_float(d.get("price")), step=100.0)
        odometer = st.number_input("Odometer", min_value=0, value=safe_int(d.get("odometer")))
        odometer_status = st.radio(
            "Odometer Statement",
            [
                "Actual mileage",
                "Not the actual mileage (discrepancy)",
                "In excess of mechanical limits",
                "Exempt (over 10 years / title shows exempt)"
            ],
            index=0
        )
        application_type = st.radio("Application Type", ["Title and Registration", "Title Only"], horizontal=True)
        reg_period = st.radio("Registration Period", ["1 year", "2 years", "3 years"], horizontal=True, index=0)
        lienholder = st.text_input("Lienholder", value=d.get("lienholder") or "")
        lienholder_address = st.text_area("Lienholder Address (look up if unclear)", value=d.get("lienholder_address") or "")
        if lienholder and not lienholder_address:
            st.caption("Address not clear on title — look up the lender’s mailing address and enter it.")
        insurance_provider = st.text_input("Insurance Provider", value=d.get("insurance_provider") or "")
        id_type = st.radio("ID Type", ["SSN", "ITIN", "EIN", "DMV Customer ID"], horizontal=True)
        ssn = st.text_input("SSN / ITIN / EIN / DMV Customer ID", value=d.get("ssn") or "")
        seller_name = st.text_input("Seller Name", value=d.get("seller_name") or d.get("seller_from_title_back") or "")
        st.markdown("**Seller Address (from title)**")
        # Pre-fill from split fields or try to parse full address
        s_street = d.get("seller_street") or ""
        s_city = d.get("seller_city") or ""
        s_state = d.get("seller_state") or ""
        s_zip = d.get("seller_zip") or ""
        if not s_street and d.get("seller_address"):
            parts = [p.strip() for p in str(d.get("seller_address")).replace("\n", ", ").split(",") if p.strip()]
            if parts:
                s_street = parts[0]
            if len(parts) > 1:
                s_city = parts[1]
            if len(parts) > 2:
                rest = parts[2].split()
                if rest:
                    s_state = rest[0]
                if len(rest) > 1:
                    s_zip = rest[-1]
        seller_street = st.text_input("Seller Street", value=s_street)
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            seller_city = st.text_input("Seller City", value=s_city)
        with sc2:
            seller_state = st.text_input("Seller State", value=s_state)
        with sc3:
            seller_zip = st.text_input("Seller Zip", value=s_zip)
        need_ny_bill = st.radio("Need New York Bill of Sale?", ["No", "Yes"], horizontal=True)
        title_already = st.radio("Title already in applicant’s name (not a separate buyer)?", ["No", "Yes"], horizontal=True,
                                 index=1 if str(d.get("title_already_in_buyer_name") or "").lower() in ("yes","true","y") else 0)
        employee_notes = st.text_area("Employee Notes", value=d.get("employee_notes") or "")
        feedback = st.text_area("Report a problem with this extraction (optional)", value="", placeholder="What went wrong? Blurry photo, missing field, etc.")

        c_back, c_next = st.columns([1, 1])
        with c_back:
            back = st.form_submit_button("← Back")
        with c_next:
            next_btn = st.form_submit_button("Next — Confirm", type="primary")

        if back:
            st.session_state.step = 1
            st.rerun()
        if next_btn:
            missing = []
            if not street or not street.strip():
                missing.append("Street address")
            if not vin or len(str(vin).strip()) < 11:
                missing.append("VIN")
            if not make or not make.strip():
                missing.append("Make")
            if not model or not model.strip():
                missing.append("Model")
            if missing:
                st.error("Required before continuing: " + ", ".join(missing))
            else:
                st.session_state.form_data = {
                    "buyer_name": buyer_name,
                    "buyer_address": f"{street}, {city}, {state} {zip_code}".strip(", "),
                    "street": street, "city": city, "state": state, "zip": zip_code,
                    "phone": phone, "email": email, "co_owner_name": co_owner_name,
                    "year": year, "make": make, "model": model, "vin": vin,
                    "body_type": body_type, "color": color, "fuel_type": fuel_type,
                    "title_number": title_number, "sale_date": sale_date,
                    "price": price, "odometer": odometer, "odometer_status": odometer_status, "reg_period": reg_period,
                    "application_type": application_type,
                    "lienholder": lienholder, "lienholder_address": lienholder_address, "insurance_provider": insurance_provider,
                    "id_type": id_type, "ssn": ssn,
                    "seller_name": seller_name, "seller_address": f"{seller_street}, {seller_city}, {seller_state} {seller_zip}".strip(", "),
                    "seller_street": seller_street, "seller_city": seller_city, "seller_state": seller_state, "seller_zip": seller_zip,
                    "need_ny_bill": need_ny_bill, "employee_notes": employee_notes,
                    "title_already_in_buyer_name": title_already,
                }
                st.session_state.step = 3
                st.rerun()

# ==================== STEP 3 ====================
elif st.session_state.step == 3:
    st.markdown('<div class="step-badge">Step 3 of 3 — Confirm & Generate</div>', unsafe_allow_html=True)
    d = st.session_state.form_data or {}
    st.success("Please confirm the summary below and generate the official forms.")

    # Fee estimator
    price = safe_float(d.get("price"))
    tax = max(price * 0.0415, 75) if price else 0
    title_fee = 15
    reg_fee = 36 if d.get("reg_period") == "2 years" else (54 if d.get("reg_period") == "3 years" else 31)
    total_est = tax + title_fee + reg_fee
    st.markdown(f"""
<div style="background:#fff8e1; border:2px solid #f9a825; border-radius:10px; padding:14px; margin:12px 0;">
<strong>Estimated fees (approximate)</strong><br>
Title: ${title_fee} &nbsp;|&nbsp; Registration: ~${reg_fee} &nbsp;|&nbsp; Sales tax (4.15%): ${tax:,.2f}<br>
<strong>Estimated total: ${total_est:,.2f}</strong><br>
<small>Confirm exact amounts with DMV. Tax has a $75 minimum.</small>
</div>
""", unsafe_allow_html=True)

    # Document checklist
    st.markdown("""
<div style="background:#e8f5e9; border:2px solid #2e7d32; border-radius:10px; padding:14px; margin:12px 0; color:#1a1a1a;">
<strong style="color:#1a1a1a;">Document checklist before DMV</strong><br>
<span style="color:#1a1a1a;">☐ Signed out-of-state title (assignment completed)<br>
☐ Bill of sale or Vehicle Price Certification<br>
☐ Proof of address (ID matches application)<br>
☐ Virginia insurance (company name filled)<br>
☐ SSN / ITIN / EIN / DMV ID entered<br>
☐ Customer signs in office</span>
</div>
""", unsafe_allow_html=True)
    st.info("Verify that the identification matches the applicant, insurance is valid, and any required lien release is available. All signatures must be completed in the office.")

    st.markdown(f"""
**Buyer:** {d.get('buyer_name') or '—'}  
**Phone:** {d.get('phone') or '—'}  
**Address:** {d.get('buyer_address') or '—'}  
**Vehicle:** {d.get('year') or ''} {d.get('make') or ''} {d.get('model') or ''}  
**VIN:** {d.get('vin') or '—'}  
**Price:** ${safe_float(d.get('price')):,.2f}  
**Sale Date:** {d.get('sale_date') or '—'}  
**Odometer:** {d.get('odometer') or '—'}  
**Registration:** {d.get('reg_period') or '—'}  
**Insurance:** {d.get('insurance_provider') or '—'}  
**Lien:** {d.get('lienholder') or 'None'}  
**Seller:** {d.get('seller_name') or '—'}  
**NY Bill of Sale:** {d.get('need_ny_bill') or 'No'}  
**Notes:** {d.get('employee_notes') or '—'}
    """)
    st.info("Verify that the identification matches the applicant, insurance is valid, and any required lien release is available. All signatures must be completed in the office.")
    st.markdown("""
<div style="background:#fff3cd; color:#000000; padding:14px; border-radius:8px; font-weight:700; font-size:1.1rem; margin-top:8px;">
Estimated fees (approximate): Title ~$15 | Registration ~$30–40 | Sales tax varies by locality. Confirm exact amounts with DMV.
</div>
""", unsafe_allow_html=True)

    if st.button("Generate Forms", type="primary"):
        zip_buf = io.BytesIO()
        individual = {}
        with zipfile.ZipFile(zip_buf, "w") as zf:
            # VSA 17A
            vsa = {
                "F[0].OWNER[0].owner_2[0].#subform[1].BusinessStreetAdd[0]": d.get("buyer_name") or "",
                "F[0].OWNER[0].owner_info-03[0].ResAddr[0]": d.get("street") or "",
                "F[0].OWNER[0].owner_info-03[0].City[0]": d.get("city") or "",
                "F[0].OWNER[0].owner_info-03[0].State[0]": d.get("state") or "",
                "F[0].OWNER[0].owner_info-03[0].Zip[0]": d.get("zip") or "",
                "F[0].OWNER[0].owner_2[0].#subform[1].TeleNum1[0]": d.get("phone") or "",
                "Year[0]": d.get("year") or "",
                "Make[0]": d.get("make") or "",
                "F[0].VEH_INFO[0].weight[0].TextField1[0]": "",
                "F[0].VEH_INFO[0].weight[0].TextField1[1]": "",
                "F[0].VEH_INFO[0].weight[0].TextField1[2]": "",
                "F[0].VEH_INFO[0].weight[0].TextField1[3]": "",
                "TextField1[1]": d.get("body_type") or "",
                "F[0].PERSONAL_PROPERTY[0].RadioButtonList[0]": "0",  # personal use
                "F[0].RegInfo[0].RadioButtonList[2]": "0",  # private registration
                "TextField1[2]": d.get("vin") or "",
                "TextField1[3]": "4",
                "F[0].OWNER[0].owner_info-03[0].WhereGaraged[0]": "NY",
                "F[0].SOURCE_OWNERSHIP[0].SalesPrice[0]": str(int(d.get("price") or 0)),
                "F[0].SOURCE_OWNERSHIP[0].PurchaseDate[0]": d.get("sale_date") or str(date.today()),
                "F[0].SOURCE_OWNERSHIP[0].PurchasedFrom[0]": d.get("seller_name") or "",
                "F[0].SOURCE_OWNERSHIP[0].StreetAdd[0]": d.get("seller_street") or d.get("seller_address") or "",
                "F[0].SOURCE_OWNERSHIP[0].City[0]": d.get("seller_city") or "",
                "F[0].SOURCE_OWNERSHIP[0].State[0]": d.get("seller_state") or "",
                "F[0].SOURCE_OWNERSHIP[0].Zip[0]": d.get("seller_zip") or "",
                "TextField2[0]": str(d.get("odometer") or ""),
                "F[0].CERT[0].LesseeName[0]": d.get("buyer_name") or "",
                "F[0].LEASE_INFO[0].LesseeName[0]": "",
                "LesseeName[0]": "",
                "SignedDate1[0]": str(date.today()),
                "SignedDate1[1]": str(date.today()),
                "F[0].INSURANCE[0].TextField5[0]": d.get("insurance_provider") or "",
                "F[0].PERSONAL_PROPERTY[0].Table1[0].Row1[0].Cell4[0]": "/1",
                "F[0].PERSONAL_PROPERTY[0].Table1[0].Row2[0].Cell4[0]": "/1",
                "F[0].PERSONAL_PROPERTY[0].Table1[0].Row3[0].Cell4[0]": "/1",
                "F[0].PERSONAL_PROPERTY[0].Table1[0].Row4[0].Cell4[0]": "/1",
                "reg_period": d.get("reg_period") or "1 year",
            }
            if d.get("ssn"):
                vsa["F[0].OWNER[0].owner_2[0].#subform[1].SSN1[0]"] = d.get("ssn")
            if d.get("lienholder"):
                vsa["F[0].LIEN[0].line02[0].LienName[0]"] = d.get("lienholder")
                vsa["F[0].LIEN[0].line3_address[0].LienHolderAdd[0]"] = d.get("lienholder_address") or ""
                vsa["F[0].LIEN[0].line01[0].RadioButtonList[0]"] = "Yes"
            else:
                vsa["F[0].LIEN[0].line01[0].RadioButtonList[0]"] = "No"
            # Always No for these
            vsa["F[0].VEH_INFO[0].FUEL_TYPE[0].#subform[2].RadioButtonList[0]"] = "1"  # low speed = No
            vsa["F[0].VEH_INFO[0].FUEL_TYPE[0].#subform[2].RadioButtonList[1]"] = "1"  # logging = No
            vsa["F[0].OWNER[0].owner_info[0].RadioButtonList[0]"] = "1"  # electronic title = No
            # Application type (0 = Title and Registration, 1 = Title Only)
            if d.get("application_type") == "Title Only":
                vsa["F[0].RegInfo[0].RadioButtonList[0]"] = "1"
            else:
                vsa["F[0].RegInfo[0].RadioButtonList[0]"] = "0"
            # Registration period
            if d.get("reg_period") == "2 years":
                vsa["F[0].RegInfo[0].RadioButtonList[1]"] = "1"
            else:
                vsa["F[0].RegInfo[0].RadioButtonList[1]"] = "0"
            # Lien
            if d.get("lienholder"):
                vsa["F[0].LIEN[0].line01[0].RadioButtonList[0]"] = "0"
            else:
                vsa["F[0].LIEN[0].line01[0].RadioButtonList[0]"] = "1"
            try:
                pdf = fill_pdf("VA_VSA_17A_Official.pdf", vsa)
                name = f"VSA_17A_{d.get('buyer_name','customer').replace(' ','_')}.pdf"
                zf.writestr(name, pdf.getvalue())
                individual[name] = pdf.getvalue()
            except Exception as e:
                st.error(f"VSA 17A: {e}")

            # Price Cert
            price_f = {
                "Text32[0]": d.get("buyer_name") or "",
                "Text32[2]": d.get("seller_name") or "",
                "Text32[4]": d.get("vin") or "",
                "Text32[6]": d.get("year") or "",
                "Text32[7]": d.get("make") or "",
                "Text32[8]": d.get("model") or "",
                "TextFieldnew[0]": str(int(d.get("price") or 0)),
                "TextFieldnew[2]": str(int(d.get("price") or 0)),
                "TextFieldnew[4]": d.get("sale_date") or "",
                "TextFieldnew[1]": str(date.today()),  # purchaser signature date
                "TextFieldnew[3]": str(date.today()),  # seller signature date
            }
            try:
                pdf = fill_pdf("VA_Vehicle_Price_Certification.pdf", price_f)
                name = f"Price_Certification_{d.get('buyer_name','customer').replace(' ','_')}.pdf"
                zf.writestr(name, pdf.getvalue())
                individual[name] = pdf.getvalue()
            except Exception as e:
                st.error(f"Price Cert: {e}")

            # VSA 70 — owner info filled, "granted to" left blank
            poa = {
                "TextField1[0]": d.get("buyer_name") or "",
                "TextField1[12]": d.get("street") or "",
                "TextField1[13]": d.get("city") or "",
                "TextField1[14]": d.get("state") or "",
                "TextField1[15]": d.get("zip") or "",
                "TextField1[1]": d.get("make") or "",
                "TextField1[3]": d.get("year") or "",
                "TextField1[4]": d.get("vin") or "",
                "TextField1[5]": d.get("title_number") or "",
                "TextField1[7]": str(date.today()),  # date signed
            }
            if d.get("ssn"):
                poa["TextField1[6]"] = d.get("ssn")
            try:
                pdf = fill_pdf("VA_VSA_70_Official.pdf", poa)
                name = f"VSA_70_{d.get('buyer_name','customer').replace(' ','_')}.pdf"
                zf.writestr(name, pdf.getvalue())
                individual[name] = pdf.getvalue()
            except Exception as e:
                st.error(f"VSA 70: {e}")

            # NY Bill of Sale
            if d.get("need_ny_bill") == "Yes":
                ny = {
                    "Seller": d.get("seller_name") or "",
                    "Name Seller": d.get("seller_name") or "",
                    "Address Seller": d.get("seller_address") or "",
                    "Buyer": d.get("buyer_name") or "",
                    "Name Buyer": d.get("buyer_name") or "",
                    "Address Buyer": d.get("buyer_address") or "",
                    "Year": d.get("year") or "",
                    "Make": d.get("make") or "",
                    "Model": d.get("model") or "",
                    "Vehicle or Hull Identification Number": d.get("vin") or "",
                    "Consideration": str(int(d.get("price") or 0)),
                    "Terms and Conditions": "Sold as-is. Signatures completed in office.",
                }
                try:
                    pdf = fill_pdf("NY_MV-912_Bill_of_Sale_Official.pdf", ny)
                    name = f"NY_Bill_of_Sale_{d.get('buyer_name','customer').replace(' ','_')}.pdf"
                    zf.writestr(name, pdf.getvalue())
                    individual[name] = pdf.getvalue()
                except Exception as e:
                    st.error(f"NY Bill of Sale: {e}")

        zip_buf.seek(0)
        st.markdown("### Download Forms")
        st.download_button("Download All Forms (ZIP)", zip_buf,
                           file_name=f"EST_Forms_{d.get('buyer_name','customer').replace(' ','_')[:20]}.zip",
                           mime="application/zip", type="primary")
        for name, data in individual.items():
            st.download_button(f"Download {name}", data, file_name=name, mime="application/pdf", use_container_width=True)
        st.success("Forms ready. Customer signs in the office.")
        # Simple daily log
        try:
            log_line = f"{date.today()} | {d.get('buyer_name','')} | {d.get('vin','')} | {d.get('phone','')}\n"
            with open("customer_log.txt", "a") as f:
                f.write(log_line)
        except:
            pass

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back to Edit"):
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("Start Over"):
            if st.session_state.get("confirm_reset"):
                st.session_state.step = 1
                st.session_state.form_data = {}
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Click Start Over again to confirm and clear all data.")
                st.rerun()

st.divider()
st.caption("© 2026 Empire State Tags. All rights reserved. This tool is for internal employee use only. Unauthorized access or distribution is prohibited.")
