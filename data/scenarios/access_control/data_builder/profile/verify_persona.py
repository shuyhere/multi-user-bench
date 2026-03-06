
import json
import random
import os

def generate_persona(pool_path):
    with open(pool_path, 'r') as f:
        pool = json.load(f)

    # Define consistency constraints
    level_min_exp = {
        "Junior": 0,
        "Mid-level": 2,
        "Senior": 5,
        "Lead": 8,
        "Manager": 10,
        "Director": 12
    }
    tenure_map_to_years = {
        "newly hired": 0,
        "1 year": 1,
        "3 years": 3,
        "5 years": 5,
        "10+ years": 10
    }

    # 1. Pick Level and Tenure first
    level = random.choice(pool['job_dimensions']['levels'])
    tenure = random.choice(pool['job_dimensions']['tenures'])

    # 2. Calculate minimum valid age
    # Base start work age = 22
    min_exp_years = level_min_exp.get(level, 0)
    tenure_years = tenure_map_to_years.get(tenure, 0)
    
    # Age must be at least 22 + max(years required for level, years spent at company)
    min_age = 22 + max(min_exp_years, tenure_years)
    max_age = pool['age_range']['max']
    
    # Ensure min <= max (basic safety, though 22+12=34 < 65)
    if min_age > max_age:
        min_age = max_age

    age = random.randint(min_age, max_age)

    gender = random.choice(pool['genders'])
    role = random.choice(pool['job_dimensions']['roles'])
    temperament = random.choice(pool['job_dimensions']['temperaments'])
    working_style = random.choice(pool['job_dimensions']['working_styles'])
    authority_level = random.choice(pool['job_dimensions']['authority_levels'])

    # Get a random responsibility for the chosen role
    responsibilities = pool['job_dimensions']['job_responsibilities'].get(role, ["general duties"])
    job_responsibility = random.choice(responsibilities)

    security_behavior = random.choice(pool['job_dimensions']['security_behaviors'])

    template = pool['templates']['description_format']
    description = template.format(
        age=age,
        gender=gender,
        level=level,
        role=role,
        tenure=tenure,
        temperament=temperament,
        working_style=working_style,
        job_responsibility=job_responsibility,
        security_behavior=security_behavior,
        authority_level=authority_level
    )
    return description

if __name__ == "__main__":
    pool_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/scenarios/access_control/data_builder/profilecollaborative_persona_pool.json")
    print("--- Generated Personas ---")
    for _ in range(5):
        print(generate_persona(pool_path))
