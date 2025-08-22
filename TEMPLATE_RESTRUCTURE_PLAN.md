# IPAM Templates Restructuring Plan

## Current Issues:
1. `ip_management_clean.html` (3,884 lines) contains multiple functions mixed together
2. `subnet_manager_fast.html` has JavaScript errors
3. Redundant templates with overlapping functionality
4. Hard to maintain and debug

## Proposed New Structure:

### 🎯 Individual Function Templates:
```
templates/
├── shared/
│   ├── base_layout.html           # Common layout with sidebar
│   ├── components/
│   │   ├── sidebar.html           # Reusable sidebar component
│   │   ├── header.html            # Reusable header component
│   │   └── modals.html            # Common modals
│   └── assets/
│       ├── common.css             # Shared styles
│       └── common.js              # Shared JavaScript functions
│
├── dashboard/
│   └── overview.html              # Main dashboard (extracted from ip_management_clean)
│
├── ip_management/
│   ├── ip_list.html               # Clean IP management interface
│   └── ip_detail_modal.html       # IP detail popup
│
├── subnet_management/
│   ├── subnet_overview.html       # Subnet cards view
│   ├── subnet_fast.html           # Fast subnet manager (fixed version)
│   └── subnet_detail_modal.html   # Subnet detail popup
│
├── vrf_monitoring/
│   ├── vrf_overview.html          # VRF monitoring cards
│   └── vrf_detail_modal.html      # VRF detail popup
│
├── tools/
│   ├── ip_auto_allocation.html    # IP auto assignment
│   ├── csv_import.html            # Bulk import
│   └── network_sections.html     # Section management
│
└── legacy/                        # Keep old files for reference
    ├── ip_management_clean.html   # Original monolithic file
    └── ip_management_advanced.html
```

## Benefits:
✅ **Easier Maintenance**: Each function in separate file
✅ **Better Performance**: Load only needed JavaScript/CSS
✅ **Reduced Redundancy**: Shared components reused
✅ **Cleaner Code**: Single responsibility per template
✅ **Faster Development**: Easier to find and modify specific features
✅ **Better Testing**: Can test individual functions independently

## Migration Strategy:
1. Create shared base layout template
2. Extract each section from ip_management_clean.html
3. Update routes to use new templates
4. Fix subnet_manager_fast.html errors
5. Test each function individually
6. Remove redundant old templates

## Priority Order:
1. Fix immediate subnet-manager error
2. Create base layout template
3. Extract dashboard section
4. Extract IP management section  
5. Extract subnet management section
6. Extract VRF monitoring section
7. Extract IP auto allocation section
