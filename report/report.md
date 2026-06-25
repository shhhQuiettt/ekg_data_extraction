# Ekstrakcja danych EKG ze zrzutu ekranu

Krzysztof Skrobała 156039

[link do repozytorium](https://github.com/shhhQuiettt/ekg_data_extraction)

# Wprowadzenie

Zadanie polega na ekstrakcji danych EKG ze zrzutu ekranu. Celem jest przekształcenie obrazu zawierającego wykres EKG w dane numeryczne. Oś Y jest podzielona na 12 kanałów (bez COI i HIS)

![](./images/P3_1.JPG)

### Oś X

Oś X powinna być skalibrowana zgodnie z poniższym obrazkiem, gdzie zaznaczony jest fragment 200ms. Z ręcznego pomiaru wynika, że jest to 226 pixeli, dając dokładność około 1.13 pixeli/ms.

![](./images/P3_3.JPG)

# Układ kodu
- `main.py` - główny plik, który wykonuje wszystkie kroki ekstrakcji danych EKG 
- `src/plots.py` - funkcje do rysowania wykresów
- `src/types.py` - plike z przydatnymi strukturami 

# Uruchomienie

## Używając uv
```bash
uv venv
source .venv/bin/activate
uv sync
python main.py --input_dir INPUT_DIR --output_dir OUTPUT_DIR [--debug_dir DEBUG_DIR]
```

## Używając pip
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --input_dir INPUT_DIR --output_dir OUTPUT_DIR [--debug_dir DEBUG_DIR]
```

Argument `--debug_dir` pozwala na zapisanie obrazów z poszczególnych kroków ekstrakcji danych, co może być przydatne do debugowania i wizualizacji procesu. Domyślnie obrazy zapiszą się do folderu `./debug_dir`. W szczególności `{image_name}_signal_function.png` pokazuje wykres funkcji EKG na tle oryginalnego obrazu

# Metodologia

## 1. Wykrycie kanałów
Pierwszym krokiem jest wykrycie linii poziomych, które reprezentują kanały EKG. Ponieważ zdjęcia są statycznymi zrzutami ekranu, można użyć metody `template matching`. W tym celu został stworzony folder `templates`, który zawiera szablony labeli kanałów. Szablony te są używane do wykrywania pozycji kanałów na obrazie. za pomocą funkcji `cv2.matchTemplate`. Żeby uniknąć błędnego wykrywania, np. szablon `I` wykrywał się z prawej strony kanału `III`, wykrywanie szablonów odbywa się w kolejności od szablonów najbardziej dokładnych do mniej dokładnych. Po każdym wykryciu szablonu, pixele z obrazka, które odpowiadają wykrytemu szablonowi, są zamalowywane na czarno, aby nie były wykrywane w kolejnych iteracjach.

### Użyte szablony:

![](report/images/template_board.png)

### Przykład __błędnego__ wykrywania szablonów:
![](report/images/wrong_templates.png)

### Wyniki wykrywania kanałów z usuwaniem wykrytych szablonów z obrazu w odpowiedniej kolejności:

![](report/images/template_matching_results.png)

## 2. Usunięcie kolorów oraz labali z obrazka.

Ponieważ będą wykrywane białe piksele jako krzywą funkcji, usuwamy białe labele z obrazka prostą różnicą obrazów za pomocą funkcji `cv2.subtract`

![](report/images/images_removed_labels.png)

## 3. Binaryzacja obrazu
Ponieważ zrzut ekranu jest standardowy, do binaryzacji wystarczy proste progowanie. W tym celu użyto funkcji `cv2.threshold` z progiem 127. W wyniku binaryzacji powstaje obraz, na którym białe piksele odpowiadają krzywej funkcji, a czarne tło.

![](report/images/images_binary.png)

## 4. Ekstrakcja obszarów z wykresami

Żeby zmniejszyć obszar poszukiwania pikseli, które odpowiadają krzywej funkcji, wycinamy z obrazu obszary, które odpowiadają wykresom. W tym celu używamy wcześniej wykrytych labeli kanałów. Dla każdego z nich dodajemy duży margines wertykalny, ponieważ niektóre kanały mają duże amplitudy. Minusem jest to że niektóry kanały zawierają fragmenty innych wykresów, a nawet całe inne kanały. Ucinamy też kilka pikseli z prawej strony (obramowanie)

Żeby zidentyfikować poprawny kanał będziemy później używać odległości do labela 

### Przykładowde wycięte obszary 
![](report/images/P5_1.JPG_1.png)
![](report/images/P5_1.JPG_2.png)


## 5. Extrakcja lini za pomocą konturów
Na każdym z wyciętych obszarów szukamy konturów za pomocą funkcji `cv2.findContours`. Następnie filtrujemy znalezione kontury, aby znaleźć ten, który odpowiada krzywej funkcji. Pierwszym filtrem jest minimalna szerokość bounding boxa, która musi wynosić przynajmniej 80% szerokości całego obszaru. 

Z tak zflitrowanych konturów wybieramy ten, który jest najbliżej labela kanału. Odległość jest mierzona jako najmniejsza odległość między punktami konturu a labela kanału.

### Przykład znalezionego konturów:
![](report/images/I_contour.png)

## 6. Przekształcenie konturu w dane numeryczne
Po znalezieniu konturu, który odpowiada krzywej funkcji, przekształcamy go w dane numeryczne

1. Najpierw dla każdego zduplikowanego `x` obliczamy średnią `y`
2. Następnie jako baseline wybieramy medianę `y`
3. Obliczamy `pixels_per_ms` jako szerokość interwału (podanego w `P3_3.JPG`) obszaru podzieloną przez 200ms
4. Tworzymy nową oś od z krokiem 1ms
5. Używamy `scipy.interpolate.interp1d` do interpolacji wartości `y` dla nowej osi `x`. Żeby uniknąć problemów z interpolacją, np. gdy funkcja ma gwałtowne zmiany, co jest częste w funkcjach EKG, używamy _interpolacji liniowej_.

Szczegóły znajdują się w funkcji `contour_to_signal_function()`

### Wyniki przekształconych funkcji
![](report/images/P3_1_signal_functions.png)
![](report/images/P5_1_signal_functions.png)
![](report/images/P6_1_signal_functions.png)
![](report/images/P7_1_signal_functions.png)


## 7. Zapis danych do pliku CSV
Na koniec zapisujemy dane do pliku CSV, gdzie każda kolumna odpowiada jednemu kanałowi, a każdy wiersz odpowiada wartościom w danym czasie (od 0 z krokiem 1ms).

