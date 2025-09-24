import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import pandas as pd
import os
import sqlite3
from pathlib import Path

# Updated path handling using pathlib
project_root = Path.cwd()
DB_PATH = project_root / 'data' / 'ocr.sqlite3'
UPLOADS_PATH = project_root / 'uploads'

class ReceiptDataset(Dataset):
    def __init__(self, data, uploads_path, transform=None):
        self.data = data
        self.uploads_path = Path(uploads_path)  # Convert to Path object
        self.transform = transform
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        file_name, raw_ocr, parsed_json = self.data[idx]
        img_path = self.uploads_path / file_name  # Use pathlib syntax
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, raw_ocr

def load_ocr_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT file_name, raw_ocr, parsed_json FROM vouchers_master')
    data = cur.fetchall()
    conn.close()
    return data

def ocr_target(text):
    return torch.tensor([len(text)], dtype=torch.float32)

def main():
    data = load_ocr_data()
    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor()
    ])
    dataset = ReceiptDataset(data, UPLOADS_PATH, transform)
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

    class SimpleOCRModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.cnn = nn.Sequential(
                nn.Conv2d(3, 16, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(16, 32, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2)
            )
            self.fc = nn.Linear(32 * 64 * 64, 128)
            self.out = nn.Linear(128, 1)
        
        def forward(self, x):
            x = self.cnn(x)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
            x = self.out(x)
            return x

    model = SimpleOCRModel()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    num_epochs = 5
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        for images, targets in dataloader:
            optimizer.zero_grad()
            outputs = model(images)
            batch_targets = torch.stack([ocr_target(t) for t in targets])
            loss = criterion(outputs, batch_targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        epoch_loss = running_loss / len(dataset)
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss:.4f}")

    # Evaluation
    model.eval()
    with torch.no_grad():
        total_loss = 0.0
        for images, targets in dataloader:
            outputs = model(images)
            batch_targets = torch.stack([ocr_target(t) for t in targets])
            loss = criterion(outputs, batch_targets)
            total_loss += loss.item() * images.size(0)
        avg_loss = total_loss / len(dataset)
        print(f"Validation Loss: {avg_loss:.4f}")

if __name__ == "__main__":
    main()