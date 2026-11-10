// Native DirectWrite WWS collection and style-selection regression check.
// Build with the Windows SDK: cl /std:c++17 /EHsc tools/windows_font_check.cpp dwrite.lib ole32.lib
#include <windows.h>
#include <dwrite_3.h>
#include <wrl/client.h>
#include <filesystem>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using Microsoft::WRL::ComPtr;
namespace fs = std::filesystem;

void check(HRESULT result) {
    if (FAILED(result)) throw std::runtime_error("DirectWrite HRESULT " + std::to_string(result));
}
void ensure(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
std::wstring text(IDWriteLocalizedStrings* names) {
    UINT32 index = 0, length = 0;
    BOOL exists = FALSE;
    check(names->FindLocaleName(L"en-us", &index, &exists));
    if (!exists) index = 0;
    check(names->GetStringLength(index, &length));
    std::wstring result(length + 1, L'\0');
    check(names->GetString(index, result.data(), length + 1));
    result.resize(length);
    return result;
}
fs::path file_path(IDWriteFontFile* file) {
    ComPtr<IDWriteFontFileLoader> loader;
    ComPtr<IDWriteLocalFontFileLoader> local;
    check(file->GetLoader(&loader));
    check(loader.As(&local));
    const void* key = nullptr;
    UINT32 key_size = 0, length = 0;
    check(file->GetReferenceKey(&key, &key_size));
    check(local->GetFilePathLengthFromKey(key, key_size, &length));
    std::wstring path(length + 1, L'\0');
    check(local->GetFilePathFromKey(key, key_size, path.data(), length + 1));
    path.resize(length);
    return fs::path(path);
}
void glyph_width(IDWriteFontFace* face, UINT32 cp, UINT32 expected) {
    UINT16 glyph = 0;
    check(face->GetGlyphIndices(&cp, 1, &glyph));
    if (!glyph && cp != 'A') return; // Latin-only packages have no Han glyph.
    ensure(glyph != 0, "Missing Latin test glyph");
    DWRITE_GLYPH_METRICS metrics{};
    check(face->GetDesignGlyphMetrics(&glyph, 1, &metrics));
    ensure(metrics.advanceWidth == expected, "Incorrect compact glyph advance");
}
int wmain(int argc, wchar_t** argv) {
    try {
        ensure(argc == 3, "Usage: windows_font_check.exe DIRECTORY EXPECTED_FAMILY_OR_DASH");
        ComPtr<IDWriteFactory3> factory;
        check(DWriteCreateFactory(DWRITE_FACTORY_TYPE_ISOLATED, __uuidof(IDWriteFactory3),
                                 reinterpret_cast<IUnknown**>(factory.GetAddressOf())));
        ComPtr<IDWriteFontSetBuilder> builder;
        check(factory->CreateFontSetBuilder(&builder));
        std::vector<ComPtr<IDWriteFontFace3>> faces;
        std::vector<fs::path> paths;
        for (const auto& entry : fs::directory_iterator(argv[1])) {
            auto ext = entry.path().extension().wstring();
            if (ext != L".ttf" && ext != L".otf") continue;
            auto path = fs::absolute(entry.path());
            ComPtr<IDWriteFontFile> file;
            ComPtr<IDWriteFontFaceReference> reference;
            ComPtr<IDWriteFontFace3> face;
            check(factory->CreateFontFileReference(path.c_str(), nullptr, &file));
            check(factory->CreateFontFaceReference(file.Get(), 0, DWRITE_FONT_SIMULATIONS_NONE, &reference));
            check(builder->AddFontFaceReference(reference.Get()));
            check(reference->CreateFontFace(&face));
            faces.push_back(face);
            paths.push_back(path);
        }
        ensure(!faces.empty(), "No test fonts");
        ComPtr<IDWriteFontSet> font_set;
        ComPtr<IDWriteFontCollection1> collection;
        check(builder->CreateFontSet(&font_set));
        check(factory->CreateFontCollectionFromFontSet(font_set.Get(), &collection));
        std::set<std::wstring> families;
        for (UINT32 i = 0; i < collection->GetFontFamilyCount(); ++i) {
            ComPtr<IDWriteFontFamily> family;
            ComPtr<IDWriteLocalizedStrings> names;
            check(collection->GetFontFamily(i, &family));
            check(family->GetFamilyNames(&names));
            families.insert(text(names.Get()));
            std::wcout << L"FAMILY " << text(names.Get()) << L"\n";
        }
        std::wstring expected(argv[2]);
        if (expected == L"-") return 0;
        ensure(families == std::set<std::wstring>{expected}, "Unexpected DirectWrite WWS family grouping");
        UINT32 index = 0;
        BOOL found = FALSE;
        check(collection->FindFamilyName(expected.c_str(), &index, &found));
        ensure(found, "Expected family cannot be selected");
        ComPtr<IDWriteFontFamily> family;
        check(collection->GetFontFamily(index, &family));
        std::set<std::tuple<int, int, int>> coordinates;
        for (size_t i = 0; i < faces.size(); ++i) {
            auto& original = faces[i];
            auto weight = original->GetWeight();
            auto stretch = original->GetStretch();
            auto style = original->GetStyle();
            ensure(coordinates.emplace(weight, stretch, style).second, "Duplicate WWS coordinates");
            ComPtr<IDWriteFont> selected;
            ComPtr<IDWriteFontFace> selected_face;
            check(family->GetFirstMatchingFont(weight, stretch, style, &selected));
            ensure(selected->GetWeight() == weight && selected->GetStretch() == stretch && selected->GetStyle() == style,
                   "Wrong weight/stretch/style selected");
            check(selected->CreateFontFace(&selected_face));
            ensure(selected_face->GetSimulations() == DWRITE_FONT_SIMULATIONS_NONE, "Synthetic style selected");
            UINT32 count = 1;
            ComPtr<IDWriteFontFile> selected_file;
            check(selected_face->GetFiles(&count, selected_file.GetAddressOf()));
            ensure(count == 1 && fs::equivalent(file_path(selected_file.Get()), paths[i]), "Wrong font file selected");
            glyph_width(selected_face.Get(), 'A', 500);
            glyph_width(selected_face.Get(), 0x4E2D, 1000);
            std::wcout << L"MATCH " << paths[i].filename().wstring() << L" weight=" << weight
                       << L" stretch=" << stretch << L" style=" << style << L"\n";
        }
        std::wcout << L"PASS " << faces.size() << L" static faces\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ERROR " << error.what() << '\n';
        return 1;
    }
}
