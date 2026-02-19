"""Seed default roles and permissions.

RBAC Matrix:
┌─────────────────────┬───────┬─────────┬─────────┐
│ Permission          │ Owner │ Manager │ Cashier │
├─────────────────────┼───────┼─────────┼─────────┤
│ product:create      │  ✓    │   ✓     │         │
│ product:read        │  ✓    │   ✓     │   ✓     │
│ product:update      │  ✓    │   ✓     │         │
│ product:delete      │  ✓    │         │         │
│ order:create        │  ✓    │   ✓     │   ✓     │
│ order:read          │  ✓    │   ✓     │   ✓     │
│ order:void          │  ✓    │   ✓     │         │
│ order:refund        │  ✓    │   ✓     │         │
│ inventory:read      │  ✓    │   ✓     │   ✓     │
│ inventory:adjust    │  ✓    │   ✓     │         │
│ report:sales        │  ✓    │   ✓     │         │
│ report:inventory    │  ✓    │   ✓     │         │
│ report:financial    │  ✓    │         │         │
│ user:create         │  ✓    │         │         │
│ user:read           │  ✓    │   ✓     │         │
│ user:update         │  ✓    │         │         │
│ user:delete         │  ✓    │         │         │
│ customer:create     │  ✓    │   ✓     │   ✓     │
│ customer:read       │  ✓    │   ✓     │   ✓     │
│ customer:update     │  ✓    │   ✓     │         │
│ store:settings      │  ✓    │         │         │
│ ai:recommendations  │  ✓    │   ✓     │   ✓     │
│ ai:forecasting      │  ✓    │   ✓     │         │
│ ai:vision           │  ✓    │   ✓     │   ✓     │
└─────────────────────┴───────┴─────────┴─────────┘
"""

from app.models.role import PermissionAction, RoleType

ROLE_PERMISSIONS: dict[RoleType, list[PermissionAction]] = {
    RoleType.OWNER: list(PermissionAction),  # All permissions
    RoleType.MANAGER: [
        PermissionAction.PRODUCT_CREATE,
        PermissionAction.PRODUCT_READ,
        PermissionAction.PRODUCT_UPDATE,
        PermissionAction.ORDER_CREATE,
        PermissionAction.ORDER_READ,
        PermissionAction.ORDER_VOID,
        PermissionAction.ORDER_REFUND,
        PermissionAction.INVENTORY_READ,
        PermissionAction.INVENTORY_ADJUST,
        PermissionAction.REPORT_SALES,
        PermissionAction.REPORT_INVENTORY,
        PermissionAction.USER_READ,
        PermissionAction.CUSTOMER_CREATE,
        PermissionAction.CUSTOMER_READ,
        PermissionAction.CUSTOMER_UPDATE,
        PermissionAction.AI_RECOMMENDATIONS,
        PermissionAction.AI_FORECASTING,
        PermissionAction.AI_VISION,
    ],
    RoleType.CASHIER: [
        PermissionAction.PRODUCT_READ,
        PermissionAction.ORDER_CREATE,
        PermissionAction.ORDER_READ,
        PermissionAction.INVENTORY_READ,
        PermissionAction.CUSTOMER_CREATE,
        PermissionAction.CUSTOMER_READ,
        PermissionAction.AI_RECOMMENDATIONS,
        PermissionAction.AI_VISION,
    ],
}
