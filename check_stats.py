import csv

total = 0
green = 0
red = 0
low_conf = 0

with open('uploads/mutation_analysis_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        if row['Color'] == 'Green':
            green += 1
        elif row['Color'] == 'Red':
            red += 1
        if row['Ambiguity'] == 'Low-confidence':
            low_conf += 1

mutation_rate = round((red / total) * 100) if total > 0 else 0

print(f'Total positions: {total}')
print(f'Conserved (Green): {green}')
print(f'Mutated (Red): {red}')
print(f'Low confidence: {low_conf}')
print(f'Mutation rate: {mutation_rate}%')
print(f'Verification: {green + red} should equal {total}')