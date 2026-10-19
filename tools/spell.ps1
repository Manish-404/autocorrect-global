param(
    [Parameter(Mandatory=$true)][string]$InFile,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [string]$Lang = 'en-US'
)
# Reads one word per line from $InFile, writes the words that the Windows spell checker accepts
# (i.e. valid words in $Lang) to $OutFile. Output is ASCII, one word per line.
Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;

[ComImport, Guid("8E018A9D-2415-4677-BF08-794EA61F94BB"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface ISpellCheckerFactory {
    [return: MarshalAs(UnmanagedType.Interface)] object get_SupportedLanguages();
    int IsSupported([MarshalAs(UnmanagedType.LPWStr)] string languageTag);
    [return: MarshalAs(UnmanagedType.Interface)] ISpellChecker CreateSpellChecker([MarshalAs(UnmanagedType.LPWStr)] string languageTag);
}

[ComImport, Guid("B6FD0B71-E2BC-4653-8D05-F197E412770B"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface ISpellChecker {
    [return: MarshalAs(UnmanagedType.LPWStr)] string get_LanguageTag();
    [return: MarshalAs(UnmanagedType.Interface)] IEnumSpellingError Check([MarshalAs(UnmanagedType.LPWStr)] string text);
}

[ComImport, Guid("803E3BD4-2828-4410-8290-418D1D73C762"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IEnumSpellingError {
    [PreserveSig] int Next([MarshalAs(UnmanagedType.Interface)] out object error);
}

[ComImport, Guid("7AB36653-1796-484B-BDFA-E74F1DB7C1DC")]
public class SpellCheckerFactoryClass { }

public static class Spell {
    public static void Run(string inFile, string outFile, string lang) {
        var factory = (ISpellCheckerFactory)new SpellCheckerFactoryClass();
        if (factory.IsSupported(lang) == 0) throw new Exception("Language not supported: " + lang);
        var checker = factory.CreateSpellChecker(lang);
        var valid = new List<string>();
        foreach (var w in File.ReadLines(inFile)) {
            var word = w.Trim();
            if (word.Length == 0) continue;
            var en = checker.Check(word);
            object err;
            int hr = en.Next(out err);   // S_OK (0) -> there is an error; S_FALSE (1) -> no errors
            if (hr != 0) valid.Add(word);
            if (err != null) Marshal.ReleaseComObject(err);
            Marshal.ReleaseComObject(en);
        }
        File.WriteAllLines(outFile, valid.ToArray());
    }
}
"@
[Spell]::Run($InFile, $OutFile, $Lang)
"done: $((Get-Content $OutFile | Measure-Object).Count) valid"
