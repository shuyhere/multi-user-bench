
import json
import os
import glob
from collections import defaultdict

output_dir = "/tmp/test_controlled_exp_v2"
files = glob.glob(os.path.join(output_dir, "*.jsonl"))

if not files:
    print("No files found!")
    exit(1)

# Group scenarios by index
scenarios_by_index = defaultdict(list)

for file_path in files:
    file_name = os.path.basename(file_path)
    with open(file_path, 'r') as f:
        for idx, line in enumerate(f):
            data = json.loads(line)
            scenarios_by_index[idx].append((file_name, data))

# Verify consistency
print(f"Verifying {len(scenarios_by_index)} scenarios across {len(files)} files...\n")

for idx, variants in scenarios_by_index.items():
    print(f"Checking Scenario #{idx + 1}...")
    
    first_file, first_data = variants[0]
    
    # Reference data
    ref_resource = first_data['resource_name']
    ref_users = first_data['all_users']
    ref_auth_users = set(first_data['authorized_users'])
    
    issues = []
    
    for filename, data in variants[1:]:
        # Check Resource Name
        if data['resource_name'] != ref_resource:
            issues.append(f"  [MISMATCH] {filename}: Resource '{data['resource_name']}' != '{ref_resource}'")
            
        # Check Users (ID, Role, Goal matches)
        # Note: We do partial check to avoid deep comparison issues if structure varies slightly, 
        # but IDs and Roles must match exactly.
        
        current_user_ids = [u['id'] for u in data['all_users']]
        ref_user_ids = [u['id'] for u in ref_users]
        
        if current_user_ids != ref_user_ids:
             issues.append(f"  [MISMATCH] {filename}: Users {current_user_ids} != {ref_user_ids}")
        else:
             # Check consistency of specific user fields
             for i, u in enumerate(data['all_users']):
                 ref_u = ref_users[i]
                 if u['role'] != ref_u['role']:
                     issues.append(f"  [MISMATCH] {filename}: User {u['id']} role '{u['role']}' != '{ref_u['role']}'")
                 if u['goal'] != ref_u['goal']:
                     # Just check first 50 chars to verify it's the same base goal
                     issues.append(f"  [MISMATCH] {filename}: User {u['id']} goal mismatch")

        # Check Authorized Users
        if set(data['authorized_users']) != ref_auth_users:
            issues.append(f"  [MISMATCH] {filename}: Authorized {data['authorized_users']} != {ref_auth_users}")

    if not issues:
        print(f"  ✅ Consistent: Used resource '{ref_resource}' with users {[u['id'] for u in ref_users]}")
    else:
        print(f"  ❌ Found {len(issues)} inconsistencies:")
        for issue in issues:
            print(issue)
            
print("\nVerification Complete.")
