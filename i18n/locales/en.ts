export default {
  "app_name": "Uni Menu v8",
  "user_name": "Student Kim",
  "user_major": "Computer Science",
  "welcome": "Welcome, {name}!",
  "point": "My Balance",
  "charge": "+ Top-up",
  "policy": [
    "📍 Lunch Only (11:30~13:30)",
    "📍 Pre-order: 4,500P / Walk-in: 5,500P",
    "📍 No-show penalty: 1,000P deducted from refund"
  ],
  "btnLang": "한국어",
  "reserve": "Reserve & Pay Now",
  "optRice0": "Rice: Regular",
  "optRice1": "Rice: Small (Eco-friendly)",
  "optRice2": "Rice: Large",
  "optMain0": "Main: Regular",
  "optMain1": "Main: Extra (+1,000P)",
  "nav0": "Home",
  "nav1": "Tickets",
  "nav2": "History",
  "nav3": "Profile",
  "nav_admin": "Admin",
  "alert": "Would you like to reserve?",
  "days": {
    "mon": "Mon",
    "tue": "Tue",
    "wed": "Wed",
    "thu": "Thu",
    "fri": "Fri"
  },
  "days_full": {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday"
  },
  "empty_menu": "No menus available.",
  "menu_types": {
    "kr": "Korean",
    "premium": "Premium",
    "takeout": "Take-out"
  },
  "my_tickets": "My Tickets",
  "hide_cancelled": "Hide cancelled tickets",
  "point_history": "Point History",
  "my_profile": "My Profile",
  "coming_soon": "Page coming soon.",
  "empty_tickets": "You have no active tickets.",
  "empty_history": "No point history found.",
  "empty_profile": "Profile settings will be available soon.",
  "student": "Student",
  "student_id": "Student ID:",
  "logout": "Logout",
  "logout_error": "An error occurred during logout.",
  "status": {
    "reserved": "Reserved",
    "used": "Used",
    "cancelled": "Cancelled"
  },
  "options": {
    "rice": "Rice Option",
    "main": "Main Option"
  },
  "payment": {
    "total": "Payment Points",
    "charge": "Point Top-up",
    "use": "Point Usage",
    "complete": "Paid",
    "used": "Used",
    "loading_tickets": "Loading tickets...",
    "loading_history": "Loading history...",
    "deleted_menu": "Deleted Menu",
    "unit": "P",
    "cancel_btn": "Cancel Reservation",
    "cancel_confirm": "Are you sure you want to cancel this reservation? The points will be refunded.",
    "cancel_success": "Your reservation has been cancelled, and points have been refunded.",
    "cancel_error": "An error occurred while cancelling your reservation.",
    "refund": "Refund (Cancelled)",
    "refund_admin": "Refund (Cancelled by Admin)",
    "admin_adjust": "Admin Point Adjustment"
  },
  "admin": {
    "dashboard": "Dashboard",
    "sub_desc": "Responsible for Smart Campus Meal system operations and reservation management.",
    "loading": "Loading data safely...",
    "processing": "Processing your request...",
    "tabs": {
      "menus": "Menus",
      "tickets": "Tickets",
      "users": "Users & Points",
      "stats": "Sales & Stats"
    },
    "menus": {
      "day_suffix": "",
      "add_menu": "Add Menu",
      "edit_menu": "Edit Menu",
      "delete_menu": "Delete Menu",
      "new_menu": "Register New Menu",
      "save": "Save",
      "cancel": "Cancel",
      "no_menus": "No menus registered for {day}.",
      "first_menu": "Register First Menu",
      "edit": "Edit",
      "delete": "Delete",
      "fields": {
        "day": "Day of Week",
        "type": "Menu Type",
        "title_ko": "Menu Title (Korean)",
        "title_en": "Menu Title (English)",
        "price": "Price (Point)",
        "price_placeholder": "e.g., 4500",
        "title_ko_placeholder": "e.g., 맛있는 매콤 제육 볶음",
        "title_en_placeholder": "e.g., Spicy Stir-fried Pork"
      },
      "alerts": {
        "fill_both": "Please fill in both Korean and English titles.",
        "saved": "New menu has been registered successfully.",
        "updated": "Menu has been updated successfully.",
        "deleted": "Menu has been deleted successfully.",
        "confirm_delete": "Are you sure you want to delete this menu? Associated reservations may be affected."
      }
    },
    "tickets": {
      "search_placeholder": "Search by name, student ID, menu...",
      "filter_all": "All",
      "filter_reserved": "Reserved",
      "filter_used": "Used",
      "filter_cancelled": "Cancelled",
      "table": {
        "student": "Student (ID)",
        "menu": "Reserved Menu (Date)",
        "price_opts": "Options & Price",
        "status": "Status",
        "action": "Actions",
        "no_info": "No info",
        "deleted_menu": "Deleted Menu",
        "rice": "Rice",
        "main": "Main",
        "rice_opt": {
          "0": "Regular",
          "1": "Small",
          "2": "Large"
        },
        "main_opt": {
          "0": "Regular",
          "1": "Extra"
        }
      },
      "empty": "No tickets found matching the filters.",
      "actions": {
        "complete_meal": "Complete Meal",
        "cancel_refund": "Cancel & Refund",
        "confirm_meal": "Mark this ticket as used (Meal Completed)?",
        "confirm_cancel": "Are you sure you want to force-cancel this reservation and refund points?",
        "success_meal": "Ticket marked as used.",
        "success_cancel": "Reservation cancelled, and points refunded."
      }
    },
    "users": {
      "search_placeholder": "Search name or student ID...",
      "table": {
        "name": "Name",
        "student_id": "Student ID",
        "role": "Role",
        "points": "Balance",
        "actions": "Point & Role Actions"
      },
      "roles": {
        "admin": "Admin",
        "student": "General Student"
      },
      "actions": {
        "adjust_points": "Adjust Points",
        "promote_admin": "Promote Admin",
        "demote_student": "Demote Student",
        "confirm_role": "Are you sure you want to change user '{name}' role to '{role}'?",
        "success_role": "User role changed successfully.",
        "adjust_modal_title": "Adjust Points Manually",
        "adjust_modal_target": "Target: {name} (ID: {student_id})",
        "adjust_amount": "Adjustment Amount (P)",
        "adjust_amount_desc": "Enter a negative value to deduct points.",
        "adjust_desc": "Adjustment Reason",
        "adjust_desc_placeholder": "e.g., Reward point, ticket penalty, etc.",
        "adjust_desc_default": "Admin adjustment",
        "adjust_alert_amount": "Please enter point amount. (Cannot be 0)",
        "adjust_success": "Points adjusted successfully. ({amount}P)",
        "self_demotion_error": "You cannot demote yourself."
      },
      "empty": "No users found matching the query."
    },
    "stats": {
      "users_count": "Active Students",
      "active_tickets": "Active Tickets",
      "total_sales": "Total Sales (Meals)",
      "total_charges": "Total Top-ups",
      "active_tickets_desc": "Unused pre-ordered tickets count",
      "total_sales_desc": "Total points deducted (excl. refunds)",
      "total_charges_desc": "Total refunds: {refunds}P",
      "log_title": "Recent System Transactions Log (Max 50)",
      "log_table": {
        "date": "Date & Time",
        "student": "Student (ID)",
        "amount": "Amount",
        "type": "Type",
        "desc": "Details",
        "charge": "Top-up",
        "refund": "Refund",
        "deduct": "Deduct",
        "no_info": "No info"
      },
      "empty_logs": "No transactions logged."
    }
  }
}