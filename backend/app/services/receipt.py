"""Receipt generation service for thermal printers."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ReceiptLine(BaseModel):
    """Single line in receipt."""
    text: str
    align: Literal["left", "center", "right"] = "left"
    bold: bool = False
    double_height: bool = False
    double_width: bool = False


class ReceiptItem(BaseModel):
    """Product item in receipt."""
    name: str
    quantity: int
    unit_price: Decimal = Field(..., decimal_places=2)
    subtotal: Decimal = Field(..., decimal_places=2)
    discount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)


class ReceiptData(BaseModel):
    """Complete receipt data for printing."""
    # Store info
    store_name: str
    store_address: str | None = None
    store_phone: str | None = None
    store_tax_id: str | None = None
    
    # Order info
    order_number: str
    order_date: datetime
    cashier_name: str
    
    # Customer info (optional)
    customer_name: str | None = None
    customer_phone: str | None = None
    
    # Items
    items: list[ReceiptItem]
    
    # Totals
    subtotal: Decimal = Field(..., decimal_places=2)
    tax_amount: Decimal = Field(..., decimal_places=2)
    discount_amount: Decimal = Field(..., decimal_places=2)
    total: Decimal = Field(..., decimal_places=2)
    
    # Payment
    payment_method: str
    amount_paid: Decimal | None = Field(None, decimal_places=2)
    change: Decimal | None = Field(None, decimal_places=2)
    
    # Footer
    note: str | None = None
    footer_message: str = "Cảm ơn quý khách!"


def generate_receipt_lines(receipt_data: ReceiptData) -> list[ReceiptLine]:
    """Generate formatted receipt lines for thermal printer (58mm/80mm)."""
    lines: list[ReceiptLine] = []
    
    # Header - Store info
    lines.append(ReceiptLine(
        text=receipt_data.store_name,
        align="center",
        bold=True,
        double_width=True,
    ))
    
    if receipt_data.store_address:
        lines.append(ReceiptLine(text=receipt_data.store_address, align="center"))
    
    if receipt_data.store_phone:
        lines.append(ReceiptLine(text=f"Tel: {receipt_data.store_phone}", align="center"))
    
    if receipt_data.store_tax_id:
        lines.append(ReceiptLine(text=f"MST: {receipt_data.store_tax_id}", align="center"))
    
    lines.append(ReceiptLine(text="=" * 32, align="center"))
    
    # Order info
    lines.append(ReceiptLine(text=f"Hóa đơn: {receipt_data.order_number}", bold=True))
    lines.append(ReceiptLine(
        text=receipt_data.order_date.strftime("%d/%m/%Y %H:%M:%S")
    ))
    lines.append(ReceiptLine(text=f"Thu ngân: {receipt_data.cashier_name}"))
    
    # Customer info
    if receipt_data.customer_name:
        lines.append(ReceiptLine(text=f"Khách: {receipt_data.customer_name}"))
    if receipt_data.customer_phone:
        lines.append(ReceiptLine(text=f"SĐT: {receipt_data.customer_phone}"))
    
    lines.append(ReceiptLine(text="-" * 32))
    
    # Items header
    lines.append(ReceiptLine(text="Sản phẩm", bold=True))
    
    # Items
    for item in receipt_data.items:
        # Product name
        lines.append(ReceiptLine(text=item.name))
        
        # Quantity x Price = Subtotal
        item_line = (
            f"  {item.quantity} x {item.unit_price:,.0f}đ = "
            f"{item.subtotal:,.0f}đ"
        )
        lines.append(ReceiptLine(text=item_line))
        
        # Discount if any
        if item.discount > 0:
            lines.append(ReceiptLine(text=f"  Giảm giá: -{item.discount:,.0f}đ"))
    
    lines.append(ReceiptLine(text="-" * 32))
    
    # Totals
    lines.append(ReceiptLine(
        text=f"Tạm tính: {receipt_data.subtotal:,.0f}đ",
        align="right",
    ))
    
    if receipt_data.tax_amount > 0:
        lines.append(ReceiptLine(
            text=f"Thuế: {receipt_data.tax_amount:,.0f}đ",
            align="right",
        ))
    
    if receipt_data.discount_amount > 0:
        lines.append(ReceiptLine(
            text=f"Giảm giá: -{receipt_data.discount_amount:,.0f}đ",
            align="right",
        ))
    
    lines.append(ReceiptLine(text="=" * 32))
    
    lines.append(ReceiptLine(
        text=f"TỔNG CỘNG: {receipt_data.total:,.0f}đ",
        align="right",
        bold=True,
        double_height=True,
    ))
    
    # Payment info
    lines.append(ReceiptLine(text="-" * 32))
    lines.append(ReceiptLine(text=f"Thanh toán: {receipt_data.payment_method}"))
    
    if receipt_data.amount_paid:
        lines.append(ReceiptLine(
            text=f"Tiền khách đưa: {receipt_data.amount_paid:,.0f}đ",
            align="right",
        ))
    
    if receipt_data.change and receipt_data.change > 0:
        lines.append(ReceiptLine(
            text=f"Tiền thừa: {receipt_data.change:,.0f}đ",
            align="right",
        ))
    
    # Note
    if receipt_data.note:
        lines.append(ReceiptLine(text="-" * 32))
        lines.append(ReceiptLine(text=f"Ghi chú: {receipt_data.note}"))
    
    # Footer
    lines.append(ReceiptLine(text="=" * 32))
    lines.append(ReceiptLine(
        text=receipt_data.footer_message,
        align="center",
        bold=True,
    ))
    lines.append(ReceiptLine(text=" "))  # Blank line for printer to cut
    
    return lines


def format_receipt_text(receipt_data: ReceiptData) -> str:
    """Generate plain text receipt for preview/testing."""
    lines = generate_receipt_lines(receipt_data)
    return "\n".join(line.text for line in lines)


def generate_esc_pos_commands(receipt_data: ReceiptData) -> bytes:
    """
    Generate ESC/POS commands for thermal printer.
    Compatible with most 58mm/80mm thermal printers.
    """
    lines = generate_receipt_lines(receipt_data)
    
    # ESC/POS command bytes
    ESC = b'\x1b'
    GS = b'\x1d'
    
    # Initialize printer
    commands = ESC + b'@'
    
    for line in lines:
        # Text alignment
        if line.align == "center":
            commands += ESC + b'a\x01'
        elif line.align == "right":
            commands += ESC + b'a\x02'
        else:
            commands += ESC + b'a\x00'
        
        # Bold
        if line.bold:
            commands += ESC + b'E\x01'
        else:
            commands += ESC + b'E\x00'
        
        # Double height/width
        if line.double_height and line.double_width:
            commands += GS + b'!\x30'  # Both
        elif line.double_height:
            commands += GS + b'!\x10'  # Height only
        elif line.double_width:
            commands += GS + b'!\x20'  # Width only
        else:
            commands += GS + b'!\x00'  # Normal
        
        # Print text
        commands += line.text.encode('utf-8') + b'\n'
    
    # Cut paper (full cut)
    commands += GS + b'V\x00'
    
    return commands
