"""
SIH26056 — Indian Airports & State Directory.

Comprehensive directory of 85+ commercial airports across all 28 States and 8 Union Territories in India.
"""

from typing import Any

INDIAN_AIRPORTS: list[dict[str, Any]] = [
    # Delhi NCT
    {"code": "DEL", "city": "New Delhi", "name": "Indira Gandhi International Airport", "state": "Delhi", "tier": 1},
    # Maharashtra
    {"code": "BOM", "city": "Mumbai", "name": "Chhatrapati Shivaji Maharaj International Airport", "state": "Maharashtra", "tier": 1},
    {"code": "PNQ", "city": "Pune", "name": "Pune International Airport", "state": "Maharashtra", "tier": 2},
    {"code": "NAG", "city": "Nagpur", "name": "Dr. Babasaheb Ambedkar International Airport", "state": "Maharashtra", "tier": 2},
    {"code": "SAG", "city": "Shirdi", "name": "Shirdi International Airport", "state": "Maharashtra", "tier": 3},
    {"code": "IXU", "city": "Aurangabad", "name": "Chhatrapati Sambhajinagar Airport", "state": "Maharashtra", "tier": 3},
    {"code": "KLH", "city": "Kolhapur", "name": "Chhatrapati Rajaram Maharaj Airport", "state": "Maharashtra", "tier": 3},
    {"code": "NDC", "city": "Nanded", "name": "Shri Guru Gobind Singh Ji Airport", "state": "Maharashtra", "tier": 3},
    {"code": "SDW", "city": "Sindhudurg", "name": "Sindhudurg Airport (Chipi)", "state": "Maharashtra", "tier": 3},
    # Karnataka
    {"code": "BLR", "city": "Bengaluru", "name": "Kempegowda International Airport", "state": "Karnataka", "tier": 1},
    {"code": "IXE", "city": "Mangalore", "name": "Mangaluru International Airport", "state": "Karnataka", "tier": 2},
    {"code": "HBX", "city": "Hubballi", "name": "Hubballi Airport", "state": "Karnataka", "tier": 3},
    {"code": "IXG", "city": "Belagavi", "name": "Belagavi Airport", "state": "Karnataka", "tier": 3},
    {"code": "MYQ", "city": "Mysuru", "name": "Mysuru Airport", "state": "Karnataka", "tier": 3},
    {"code": "GBI", "city": "Kalaburagi", "name": "Kalaburagi Airport", "state": "Karnataka", "tier": 3},
    {"code": "RQY", "city": "Shivamogga", "name": "Kuvempu Airport", "state": "Karnataka", "tier": 3},
    {"code": "IXX", "city": "Bidar", "name": "Bidar Airport", "state": "Karnataka", "tier": 3},
    # Tamil Nadu
    {"code": "MAA", "city": "Chennai", "name": "Chennai International Airport", "state": "Tamil Nadu", "tier": 1},
    {"code": "CJB", "city": "Coimbatore", "name": "Coimbatore International Airport", "state": "Tamil Nadu", "tier": 2},
    {"code": "IXM", "city": "Madurai", "name": "Madurai Airport", "state": "Tamil Nadu", "tier": 2},
    {"code": "TRZ", "city": "Tiruchirappalli", "name": "Tiruchirappalli International Airport", "state": "Tamil Nadu", "tier": 2},
    {"code": "TCR", "city": "Thoothukudi", "name": "Tuticorin Airport", "state": "Tamil Nadu", "tier": 3},
    {"code": "SXV", "city": "Salem", "name": "Salem Airport", "state": "Tamil Nadu", "tier": 3},
    # West Bengal
    {"code": "CCU", "city": "Kolkata", "name": "Netaji Subhash Chandra Bose International Airport", "state": "West Bengal", "tier": 1},
    {"code": "IXB", "city": "Bagdogra", "name": "Bagdogra International Airport (Siliguri)", "state": "West Bengal", "tier": 2},
    {"code": "RDP", "city": "Durgapur", "name": "Kazi Nazrul Islam Airport", "state": "West Bengal", "tier": 3},
    {"code": "COH", "city": "Cooch Behar", "name": "Cooch Behar Airport", "state": "West Bengal", "tier": 3},
    # Telangana
    {"code": "HYD", "city": "Hyderabad", "name": "Rajiv Gandhi International Airport", "state": "Telangana", "tier": 1},
    # Gujarat
    {"code": "AMD", "city": "Ahmedabad", "name": "Sardar Vallabhbhai Patel International Airport", "state": "Gujarat", "tier": 1},
    {"code": "STV", "city": "Surat", "name": "Surat International Airport", "state": "Gujarat", "tier": 2},
    {"code": "BDQ", "city": "Vadodara", "name": "Vadodara Airport", "state": "Gujarat", "tier": 2},
    {"code": "HSR", "city": "Rajkot", "name": "Rajkot International Airport (Hirasar)", "state": "Gujarat", "tier": 2},
    {"code": "BHU", "city": "Bhavnagar", "name": "Bhavnagar Airport", "state": "Gujarat", "tier": 3},
    {"code": "BHJ", "city": "Bhuj", "name": "Bhuj Airport", "state": "Gujarat", "tier": 3},
    {"code": "JGA", "city": "Jamnagar", "name": "Jamnagar Airport", "state": "Gujarat", "tier": 3},
    {"code": "PBD", "city": "Porbandar", "name": "Porbandar Airport", "state": "Gujarat", "tier": 3},
    {"code": "IXY", "city": "Kandla", "name": "Kandla Airport", "state": "Gujarat", "tier": 3},
    {"code": "IXK", "city": "Keshod", "name": "Keshod Airport", "state": "Gujarat", "tier": 3},
    # Rajasthan
    {"code": "JAI", "city": "Jaipur", "name": "Jaipur International Airport", "state": "Rajasthan", "tier": 2},
    {"code": "UDR", "city": "Udaipur", "name": "Maharana Pratap Airport", "state": "Rajasthan", "tier": 2},
    {"code": "JDH", "city": "Jodhpur", "name": "Jodhpur Airport", "state": "Rajasthan", "tier": 2},
    {"code": "JSA", "city": "Jaisalmer", "name": "Jaisalmer Airport", "state": "Rajasthan", "tier": 3},
    {"code": "BKB", "city": "Bikaner", "name": "Nal Airport", "state": "Rajasthan", "tier": 3},
    {"code": "KQH", "city": "Kishangarh", "name": "Kishangarh Airport (Ajmer)", "state": "Rajasthan", "tier": 3},
    # Uttar Pradesh
    {"code": "LKO", "city": "Lucknow", "name": "Chaudhary Charan Singh International Airport", "state": "Uttar Pradesh", "tier": 1},
    {"code": "VNS", "city": "Varanasi", "name": "Lal Bahadur Shastri International Airport", "state": "Uttar Pradesh", "tier": 2},
    {"code": "IXD", "city": "Prayagraj", "name": "Prayagraj Airport", "state": "Uttar Pradesh", "tier": 2},
    {"code": "AYJ", "city": "Ayodhya", "name": "Maharishi Valmiki International Airport", "state": "Uttar Pradesh", "tier": 2},
    {"code": "GOP", "city": "Gorakhpur", "name": "Mahayogi Gorakhnath Airport", "state": "Uttar Pradesh", "tier": 3},
    {"code": "AGR", "city": "Agra", "name": "Agra Airport (Kheria)", "state": "Uttar Pradesh", "tier": 3},
    {"code": "BEK", "city": "Bareilly", "name": "Bareilly Airport", "state": "Uttar Pradesh", "tier": 3},
    {"code": "KNU", "city": "Kanpur", "name": "Kanpur Airport", "state": "Uttar Pradesh", "tier": 3},
    {"code": "HDO", "city": "Hindon", "name": "Hindon Airport (Ghaziabad)", "state": "Uttar Pradesh", "tier": 3},
    # Bihar
    {"code": "PAT", "city": "Patna", "name": "Jay Prakash Narayan International Airport", "state": "Bihar", "tier": 2},
    {"code": "GAY", "city": "Gaya", "name": "Gaya International Airport", "state": "Bihar", "tier": 3},
    {"code": "DBG", "city": "Darbhanga", "name": "Darbhanga Airport", "state": "Bihar", "tier": 3},
    # Kerala
    {"code": "COK", "city": "Kochi", "name": "Cochin International Airport", "state": "Kerala", "tier": 1},
    {"code": "TRV", "city": "Thiruvananthapuram", "name": "Thiruvananthapuram International Airport", "state": "Kerala", "tier": 2},
    {"code": "CCJ", "city": "Kozhikode", "name": "Calicut International Airport", "state": "Kerala", "tier": 2},
    {"code": "CNN", "city": "Kannur", "name": "Kannur International Airport", "state": "Kerala", "tier": 2},
    # Goa
    {"code": "GOI", "city": "Dabolim", "name": "Dabolim Airport (Goa)", "state": "Goa", "tier": 2},
    {"code": "GOX", "city": "Mopa", "name": "Manohar International Airport (Mopa)", "state": "Goa", "tier": 2},
    # Assam
    {"code": "GAU", "city": "Guwahati", "name": "Lokpriya Gopinath Bordoloi International Airport", "state": "Assam", "tier": 2},
    {"code": "DIB", "city": "Dibrugarh", "name": "Dibrugarh Airport", "state": "Assam", "tier": 3},
    {"code": "IXS", "city": "Silchar", "name": "Silchar Airport", "state": "Assam", "tier": 3},
    {"code": "JRH", "city": "Jorhat", "name": "Jorhat Airport", "state": "Assam", "tier": 3},
    {"code": "TEZ", "city": "Tezpur", "name": "Tezpur Airport", "state": "Assam", "tier": 3},
    {"code": "IXI", "city": "Lilabari", "name": "Lilabari Airport (North Lakhimpur)", "state": "Assam", "tier": 3},
    {"code": "RUP", "city": "Rupsi", "name": "Rupsi Airport", "state": "Assam", "tier": 3},
    # Odisha
    {"code": "BBI", "city": "Bhubaneswar", "name": "Biju Patnaik International Airport", "state": "Odisha", "tier": 2},
    {"code": "JRG", "city": "Jharsuguda", "name": "Veer Surendra Sai Airport", "state": "Odisha", "tier": 3},
    {"code": "RRK", "city": "Rourkela", "name": "Rourkela Airport", "state": "Odisha", "tier": 3},
    {"code": "UKE", "city": "Utkela", "name": "Utkela Airport", "state": "Odisha", "tier": 3},
    # Andhra Pradesh
    {"code": "VTZ", "city": "Visakhapatnam", "name": "Visakhapatnam International Airport", "state": "Andhra Pradesh", "tier": 2},
    {"code": "VGA", "city": "Vijayawada", "name": "Vijayawada International Airport", "state": "Andhra Pradesh", "tier": 2},
    {"code": "TIR", "city": "Tirupati", "name": "Tirupati International Airport", "state": "Andhra Pradesh", "tier": 2},
    {"code": "RJA", "city": "Rajahmundry", "name": "Rajahmundry Airport", "state": "Andhra Pradesh", "tier": 3},
    {"code": "CDP", "city": "Kadapa", "name": "Kadapa Airport", "state": "Andhra Pradesh", "tier": 3},
    {"code": "KJB", "city": "Kurnool", "name": "Uyyalawada Narasimha Reddy Airport", "state": "Andhra Pradesh", "tier": 3},
    # Madhya Pradesh
    {"code": "IDR", "city": "Indore", "name": "Devi Ahilyabai Holkar Airport", "state": "Madhya Pradesh", "tier": 2},
    {"code": "BHO", "city": "Bhopal", "name": "Raja Bhoj Airport", "state": "Madhya Pradesh", "tier": 2},
    {"code": "GWL", "city": "Gwalior", "name": "Rajmata Vijaya Raje Scindia Airport", "state": "Madhya Pradesh", "tier": 3},
    {"code": "JLR", "city": "Jabalpur", "name": "Dumna Airport", "state": "Madhya Pradesh", "tier": 3},
    {"code": "HJR", "city": "Khajuraho", "name": "Khajuraho Airport", "state": "Madhya Pradesh", "tier": 3},
    # Punjab & Chandigarh
    {"code": "ATQ", "city": "Amritsar", "name": "Sri Guru Ram Dass Jee International Airport", "state": "Punjab", "tier": 2},
    {"code": "IXC", "city": "Chandigarh", "name": "Shaheed Bhagat Singh International Airport", "state": "Chandigarh", "tier": 2},
    {"code": "AIP", "city": "Adampur", "name": "Adampur Airport (Jalandhar)", "state": "Punjab", "tier": 3},
    {"code": "BUP", "city": "Bathinda", "name": "Bathinda Airport", "state": "Punjab", "tier": 3},
    # Jammu & Kashmir
    {"code": "SXR", "city": "Srinagar", "name": "Sheikh ul-Alam International Airport", "state": "Jammu & Kashmir", "tier": 2},
    {"code": "IXJ", "city": "Jammu", "name": "Jammu Airport", "state": "Jammu & Kashmir", "tier": 2},
    # Ladakh
    {"code": "IXL", "city": "Leh", "name": "Kushok Bakula Rimpochee Airport", "state": "Ladakh", "tier": 2},
    # Uttarakhand
    {"code": "DED", "city": "Dehradun", "name": "Jolly Grant Airport", "state": "Uttarakhand", "tier": 2},
    {"code": "PGH", "city": "Pantnagar", "name": "Pantnagar Airport", "state": "Uttarakhand", "tier": 3},
    # Jharkhand
    {"code": "IXR", "city": "Ranchi", "name": "Birsa Munda Airport", "state": "Jharkhand", "tier": 2},
    {"code": "DGH", "city": "Deoghar", "name": "Deoghar Airport", "state": "Jharkhand", "tier": 3},
    # Chhattisgarh
    {"code": "RPR", "city": "Raipur", "name": "Swami Vivekananda Airport", "state": "Chhattisgarh", "tier": 2},
    {"code": "JGB", "city": "Jagdalpur", "name": "Jagdalpur Airport", "state": "Chhattisgarh", "tier": 3},
    {"code": "PAB", "city": "Bilaspur", "name": "Bilaspur Airport", "state": "Chhattisgarh", "tier": 3},
    # North East States
    {"code": "IXA", "city": "Agartala", "name": "Maharaja Bir Bikram Airport", "state": "Tripura", "tier": 2},
    {"code": "IMF", "city": "Imphal", "name": "Bir Tikendrajit International Airport", "state": "Manipur", "tier": 2},
    {"code": "DMU", "city": "Dimapur", "name": "Dimapur Airport", "state": "Nagaland", "tier": 3},
    {"code": "AJL", "city": "Aizawl", "name": "Lengpui Airport", "state": "Mizoram", "tier": 3},
    {"code": "SHL", "city": "Shillong", "name": "Shillong Airport (Umroi)", "state": "Meghalaya", "tier": 3},
    {"code": "HGI", "city": "Itanagar", "name": "Donyi Polo Airport (Hollongi)", "state": "Arunachal Pradesh", "tier": 3},
    {"code": "PYG", "city": "Pakyong", "name": "Pakyong Airport (Gangtok)", "state": "Sikkim", "tier": 3},
    # Himachal Pradesh
    {"code": "DHM", "city": "Dharamshala", "name": "Kangra Airport (Gaggal)", "state": "Himachal Pradesh", "tier": 3},
    {"code": "KUU", "city": "Kullu", "name": "Kullu–Manali Airport (Bhuntar)", "state": "Himachal Pradesh", "tier": 3},
    {"code": "SLV", "city": "Shimla", "name": "Shimla Airport", "state": "Himachal Pradesh", "tier": 3},
    # Island & UTs
    {"code": "IXZ", "city": "Port Blair", "name": "Veer Savarkar International Airport", "state": "Andaman & Nicobar Islands", "tier": 2},
    {"code": "AGX", "city": "Agatti", "name": "Agatti Airport", "state": "Lakshadweep", "tier": 3},
    {"code": "PNY", "city": "Puducherry", "name": "Puducherry Airport", "state": "Puducherry", "tier": 3},
    {"code": "DIU", "city": "Diu", "name": "Diu Airport", "state": "Dadra and Nagar Haveli and Daman and Diu", "tier": 3},
]

AIRPORTS_BY_CODE: dict[str, dict[str, Any]] = {a["code"]: a for a in INDIAN_AIRPORTS}

INDIAN_STATES: list[str] = sorted(list({a["state"] for a in INDIAN_AIRPORTS}))
