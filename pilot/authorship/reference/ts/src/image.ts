/** Обработка изображений статьи: масштабирование ближайшим соседом. Об авторах не знает. */
export type Pixel = number[];

export interface Image {
  width: number;
  height: number;
  pixels: Pixel[];
}

export function resize(img: Image, width: number, height: number): Image {
  const pixels: Pixel[] = [];
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const sx = Math.floor((x * img.width) / width);
      const sy = Math.floor((y * img.height) / height);
      pixels.push(img.pixels[sy * img.width + sx] ?? [0, 0, 0, 0]);
    }
  }
  return { width, height, pixels };
}

/** Конвейер изображения статьи. */
export function pipeline(img: Image, width: number, height: number): Image {
  return resize(img, width, height);
}
