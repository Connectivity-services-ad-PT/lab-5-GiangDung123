import random


def detect(image_name: str):

    labels = [
        "person",
        "car",
        "motorbike",
        "backpack",
        "bicycle"
    ]

    result = []

    number = random.randint(1, 3)

    result.extend(
        {
            "label": random.choice(labels),
            "confidence": round(random.uniform(0.75, 0.99), 2),
            "bbox": [
                random.randint(0, 200),
                random.randint(0, 200),
                random.randint(250, 450),
                random.randint(250, 450),
            ],
        }
        for _ in range(number)
    )
    return result