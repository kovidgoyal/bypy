/*
 * Copyright (C) 2020 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */

#pragma once

#define UNICODE

#ifdef _WIN32
#define _WIN32_WINNT 0x0502
#define WINDOWS_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <limits.h>
#include <pwd.h>
#endif
#include <stdlib.h>
#include <errno.h>
#include <sys/stat.h>
#include <Python.h>
#include <frameobject.h>
#include <stdio.h>
#include <string.h>
#include <bypy-data-index.h>
#define fatal(...) { log_error(__VA_ARGS__); exit(EXIT_FAILURE); }
#define arraysz(x) (sizeof(x)/sizeof(x[0]))

static bool use_os_log = false;

#ifdef _WIN32
#define sn_printf(a, b, ...) _snprintf_s(a, b, b-1, __VA_ARGS__)

static void
log_error(const char *fmt, ...) {
    va_list ar;
    va_start(ar, fmt);
    vfprintf(stderr, fmt, ar);
    va_end(ar);
	fprintf(stderr, "\n");
}

static bool stdout_is_a_tty = false, stderr_is_a_tty = false;
static DWORD console_old_mode = 0;
static UINT code_page = CP_UTF8;
static bool console_mode_changed = false;

static void
detect_tty(void) {
    stdout_is_a_tty = _isatty(_fileno(stdout));
    stderr_is_a_tty = _isatty(_fileno(stderr));
}

static void
setup_vt_terminal_mode(void) {
    if (stdout_is_a_tty || stderr_is_a_tty) {
        HANDLE h = GetStdHandle(stdout_is_a_tty ? STD_OUTPUT_HANDLE : STD_ERROR_HANDLE);
        if (h != INVALID_HANDLE_VALUE) {
            if (GetConsoleMode(h, &console_old_mode)) {
                console_mode_changed = true;
                SetConsoleMode(h, console_old_mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
            }
        }
    }
}

static void
restore_vt_terminal_mode(void) {
    if (console_mode_changed) SetConsoleMode(GetStdHandle(stdout_is_a_tty ? STD_OUTPUT_HANDLE : STD_ERROR_HANDLE), console_old_mode);
}

static void
cleanup_console_state() {
    if (code_page != CP_UTF8) SetConsoleOutputCP(CP_UTF8);
    restore_vt_terminal_mode();
}
#else
#define sn_printf snprintf
static void
log_error(const char *fmt, ...) __attribute__ ((format (printf, 1, 2)));


static void
log_error(const char *fmt, ...) {
    va_list ar;
    struct timeval tv;
#ifdef __APPLE__
    // Apple does not provide a varargs style os_logv
    char logbuf[16 * 1024] = {0};
#else
    char logbuf[4];
#endif
    char *p = logbuf;
#define bufprint(func, ...) { if ((size_t)(p - logbuf) < sizeof(logbuf) - 2) { p += func(p, sizeof(logbuf) - (p - logbuf), __VA_ARGS__); } }
    if (!use_os_log) {  // Apple's os_log already records timestamps
        gettimeofday(&tv, NULL);
        struct tm *tmp = localtime(&tv.tv_sec);
        if (tmp) {
            char tbuf[256] = {0}, buf[256] = {0};
            if (strftime(buf, sizeof(buf), "%j %H:%M:%S.%%06u", tmp) != 0) {
                snprintf(tbuf, sizeof(tbuf), buf, tv.tv_usec);
                fprintf(stderr, "[%s] ", tbuf);
            }
        }
    }
    va_start(ar, fmt);
    if (use_os_log) { bufprint(vsnprintf, fmt, ar); }
    else vfprintf(stderr, fmt, ar);
    va_end(ar);
#ifdef __APPLE__
    if (use_os_log) os_log(OS_LOG_DEFAULT, "%{public}s", logbuf);
#endif
    if (!use_os_log) fprintf(stderr, "\n");
}
#endif

#ifdef _WIN32
// on Windows the Python DLL is delay loaded so cant use Py_RETURN_NONE
#define RETURN_NONE return Py_BuildValue("s", NULL);
static PyObject *WindowsError = NULL;
static PyObject *RuntimeError = NULL;
static PyObject *OSError = NULL;
static PyObject *FileNotFoundError = NULL;
#else
#define RETURN_NONE Py_RETURN_NONE
#define RuntimeError PyExc_RuntimeError
#define OSError PyExc_OSError
#define FileNotFoundError PyExc_FileNotFoundError
#endif

#ifndef _WIN32
static int
_get_errno(int *err) {
    *err = errno;
    return 0;
}
#endif

static PyObject*
read_file(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *ans = NULL;
#ifdef _WIN32
    PyObject *pkey;
    if (!PyArg_ParseTuple(args, "U", &pkey)) return NULL;
    wchar_t *path = PyUnicode_AsWideCharString(pkey, NULL);
    if (!path) return NULL;
    FILE *f = _wfopen(path, L"rb");
    PyMem_Free(path);
#else
    const char *path;
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    FILE *f = fopen(path, "rb");
#endif
    int err;
    _get_errno(&err);
    if (!f) return PyErr_SetFromErrnoWithFilenameObject(err == ENOENT ? FileNotFoundError : OSError, PyTuple_GET_ITEM(args, 0));
#define E {fclose(f); Py_CLEAR(ans); return PyErr_SetFromErrnoWithFilenameObject(OSError, PyTuple_GET_ITEM(args, 0)); }
    if (fseek(f, 0, SEEK_END) != 0) E;
    long sz = ftell(f);
    if (sz == -1) E;
    if (fseek(f, 0, SEEK_SET) != 0) E;
    ans = PyBytes_FromStringAndSize(NULL, sz);
    if (!ans) { fclose(f); return NULL; }
    char *data = PyBytes_AS_STRING(ans);
    long pos = 0;
    while (sz > pos) {
        size_t n = fread(data + pos, 1, sz - pos, f);
        if (n == 0) {
            if (ferror(f)) { fclose(f); Py_CLEAR(ans); PyErr_SetString(OSError, "Failed to read from file"); return NULL; }
            break;
        }
        pos += n;
    }
    fclose(f);
    if (pos < sz) { Py_CLEAR(ans); PyErr_SetString(OSError, "file changed while reading it"); return NULL; }
    return ans;
#undef E
}


static PyObject*
getenv_wrapper(PyObject *self, PyObject *args) {
    (void)self;
#ifdef _WIN32
    PyObject *pkey;
    if (!PyArg_ParseTuple(args, "U", &pkey)) return NULL;
    wchar_t *wkey = PyUnicode_AsWideCharString(pkey, NULL), *wval;
    if (!wkey) return NULL;
    size_t len;
    errno_t err = _wdupenv_s(&wval, &len, wkey);
    PyMem_Free(wkey);
    if (err) return PyErr_NoMemory();
    if (!len) RETURN_NONE;
    PyObject *ans = PyUnicode_FromWideChar(wval, len - 1);
    free(wval);
    return ans;
#else
    const char *key;
    if (!PyArg_ParseTuple(args, "s", &key)) return NULL;
    const char *val = getenv(key);
    if (!val) RETURN_NONE;
    return PyUnicode_FromString(val);
#endif
}

static PyObject*
setenv_wrapper(PyObject *self, PyObject *args) {
    (void)self;
#ifdef _WIN32
    PyObject *pkey, *pval = NULL;
    if (!PyArg_ParseTuple(args, "U|U", &pkey, &pval)) return NULL;
    wchar_t *wkey = PyUnicode_AsWideCharString(pkey, NULL), *wval = NULL;
    if (!wkey) return NULL;
    if (pval) {
        wval = PyUnicode_AsWideCharString(pval, NULL);
        if (!wval) { PyMem_Free(wkey); return NULL; }
    }
    BOOL ok = SetEnvironmentVariableW(wkey, wval ? wval : L"");
    PyMem_Free(wkey); PyMem_Free(wval);
    if (!ok) return PyErr_SetFromWindowsErr(0);
#else
    const char *key, *val = NULL;
    if (!PyArg_ParseTuple(args, "s|s", &key, &val)) return NULL;
    int ret = 0;
    if (val) ret = setenv(key, val, 1);
    else ret = unsetenv(key);
    if (ret != 0) return PyErr_SetFromErrno(PyExc_OSError);
#endif
    RETURN_NONE;
}

static PyObject*
get_home_directory(PyObject *self, PyObject *args) {
    (void)self; (void)args;
#ifdef _WIN32
    LPWSTR dest = PyMem_Calloc(sizeof(wchar_t), 32 * 1024);
    if (!dest) { return PyErr_NoMemory(); }
    DWORD sz = ExpandEnvironmentStringsW(L"%USERPROFILE%", dest, 32 * 1024);
    PyObject *ans = NULL;
    if (dest[0] != '%') {
        ans = PyUnicode_FromWideChar(dest, sz);
    } else {
        if (_wgetenv(L"HOMEDRIVE") && _wgetenv(L"HOMEPATH")) {
            sz = ExpandEnvironmentStringsW(L"%HOMEDRIVE%%HOMEPATH%", dest, 32 * 1024);
            ans = PyUnicode_FromWideChar(dest, sz);
        } else ans = PyUnicode_FromString("");
    }
    PyMem_Free(dest);
    return ans;
#else
    const char *home = getenv("HOME");
    if (!home) {
        struct passwd *pwd = getpwuid(getuid());
        if (!pwd) return PyErr_SetFromErrno(PyExc_OSError);
        home = pwd->pw_dir;
    }
    if (!home) home = "";
    return PyUnicode_FromString(home);
#endif
}

static PyObject*
show_error_message(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *pt, *pm;
    if (!PyArg_ParseTuple(args, "UU", &pt, &pm)) return NULL;
#ifdef _WIN32
    wchar_t title[256] = {0}, text[4096] = {0};
    PyUnicode_AsWideChar(pt, title, arraysz(title)-1);
    PyUnicode_AsWideChar(pm, text, arraysz(text)-1);
    MessageBoxW(NULL, text, title, MB_ICONERROR|MB_OK);
#else
    PyObject_Print(pt, stderr, Py_PRINT_RAW);
    fprintf(stderr, "\n");
    PyObject_Print(pm, stderr, Py_PRINT_RAW);
    fprintf(stderr, "\n");
#endif
    return PyBool_FromLong(1);
}

#ifdef _WIN32
#define MAP_FAILED NULL
static HANDLE datastore_file_handle = INVALID_HANDLE_VALUE;
static HANDLE datastore_mmap_handle = INVALID_HANDLE_VALUE;
#else
static int datastore_fd = -1;
static size_t datastore_len = 0;
#endif
static char *datastore_ptr = MAP_FAILED;

static inline void
free_frozen_data(void) {
#ifdef _WIN32
    if (datastore_ptr != MAP_FAILED) {
        UnmapViewOfFile(datastore_ptr);
        datastore_ptr = MAP_FAILED;
    }
    if (datastore_mmap_handle != INVALID_HANDLE_VALUE) {
        CloseHandle(datastore_mmap_handle); datastore_mmap_handle = INVALID_HANDLE_VALUE;
    }
    if (datastore_file_handle != INVALID_HANDLE_VALUE) {
        CloseHandle(datastore_file_handle); datastore_file_handle = INVALID_HANDLE_VALUE;
    }
#else
    if (datastore_ptr != MAP_FAILED) {
        munmap(datastore_ptr, datastore_len);
        datastore_ptr = MAP_FAILED;
        datastore_len = 0;
    }
    if (datastore_fd > -1) {
        while (close(datastore_fd) != 0 && errno == EINTR);
        datastore_fd = -1;
    }
#endif
}

#ifdef _WIN32

static int GUI_APP = 0;
static void
show_windows_error_box(const wchar_t *msg) {
    if (GUI_APP) {
        MessageBeep(MB_ICONERROR);
        MessageBoxW(NULL, msg, L"Unhandled error", MB_OK|MB_ICONERROR);
    }
}


static int
_show_error(const wchar_t *preamble, const wchar_t *msg, const int code) {
    static wchar_t buf[4096];
	static char utf8_buf[4096] = {0};
	int n = WideCharToMultiByte(CP_UTF8, 0, preamble, -1, utf8_buf, sizeof(utf8_buf) - 1, NULL, NULL);
	if (n > 0) fprintf(stderr, "%s\r\n  ", utf8_buf);
	n = WideCharToMultiByte(CP_UTF8, 0, msg, -1, utf8_buf, sizeof(utf8_buf) - 1, NULL, NULL);
	if (n > 0) fprintf(stderr, "%s (Error Code: %d)\r\n ", utf8_buf, code);
    fflush(stderr);

    if (GUI_APP) {
        _snwprintf_s(buf, arraysz(buf), _TRUNCATE, L"%ls\r\n  %ls (Error Code: %d)\r\n", preamble, msg, code);
        show_windows_error_box(buf);
    }
    return code;
}

int
show_last_error_crt(wchar_t *preamble) {
    wchar_t buf[1000];
    int err = 0;

    _get_errno(&err);
    _wcserror_s(buf, 1000, err);
    return _show_error(preamble, buf, err);
}

int
show_last_error(wchar_t *preamble) {
    wchar_t *msg = NULL;
    DWORD dw = GetLastError();
    int ret;

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPWSTR)&msg,
        0,
        NULL );

    ret = _show_error(preamble, msg, (int)dw);
    if (msg != NULL) LocalFree(msg);
    return ret;
}


static void
bypy_setup_python(const char* python_dll) {
    if (FAILED(__HrLoadAllImportsForDll(python_dll)))
        ExitProcess(_show_error(L"Failed to delay load the python DLL", L"", 1));
}

static void
setup_windows_exceptions(void) {
    PyObject *d = PyDict_New(), *val, *tb;
    PyRun_String("raise WindowsError('foo')", Py_single_input, d, d);
    PyErr_Fetch(&WindowsError, &val, &tb);
    Py_CLEAR(val); Py_CLEAR(tb);

    PyRun_String("raise OSError('foo')", Py_single_input, d, d);
    PyErr_Fetch(&OSError, &val, &tb);
    Py_CLEAR(val); Py_CLEAR(tb);

    PyRun_String("raise FileNotFoundError('foo')", Py_single_input, d, d);
    PyErr_Fetch(&FileNotFoundError, &val, &tb);
    Py_CLEAR(val); Py_CLEAR(tb);

    PyRun_String("raise RuntimeError('foo')", Py_single_input, d, d);
    PyErr_Fetch(&RuntimeError, &val, &tb);
    Py_CLEAR(val); Py_CLEAR(tb);
    Py_CLEAR(d);
}
#endif

static PyObject*
initialize_data_access(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *path;
    if (!PyArg_ParseTuple(args, "U", &path)) return NULL;
    if (PyUnicode_READY(path) != 0) return NULL;
#ifdef _WIN32
    wchar_t* wpath = PyUnicode_AsWideCharString(path, NULL);
    if (!wpath) return NULL;
    datastore_file_handle = CreateFileW(wpath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_READONLY | FILE_FLAG_RANDOM_ACCESS, NULL);
    PyMem_Free(wpath);
    if (datastore_file_handle == INVALID_HANDLE_VALUE) return PyErr_SetExcFromWindowsErrWithFilenameObject(WindowsError, 0, path);
    datastore_mmap_handle = CreateFileMappingW(datastore_file_handle, NULL, PAGE_READONLY, 0, 0, NULL);
    if (datastore_mmap_handle == INVALID_HANDLE_VALUE) return PyErr_SetExcFromWindowsErrWithFilenameObject(WindowsError, 0, path);
    datastore_ptr = MapViewOfFile(datastore_mmap_handle, FILE_MAP_READ, 0, 0, 0);
    if (datastore_ptr == MAP_FAILED) return PyErr_SetExcFromWindowsErrWithFilenameObject(WindowsError, 0, path);
#else
    do {
        datastore_fd = open(PyUnicode_AsUTF8(path), O_RDONLY | O_CLOEXEC);
        if (datastore_fd == -1 && errno != EINTR) return PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, path);
    } while(datastore_fd == -1);
    off_t sz = lseek(datastore_fd, 0, SEEK_END);
    if (sz == -1) { PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, path); close(datastore_fd); datastore_fd = -1; return NULL; }
    datastore_len = (size_t)sz;
    lseek(datastore_fd, 0, SEEK_SET);
    datastore_ptr = mmap(0, datastore_len, PROT_READ, MAP_SHARED, datastore_fd, 0);
    if (datastore_ptr == MAP_FAILED) { PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, path); close(datastore_fd); datastore_fd = -1; return NULL; }
#endif
    return PyBytes_FromStringAndSize(filesystem_tree, sizeof(filesystem_tree));
}


static PyObject*
get_data_at(PyObject *self, PyObject *args) {
    (void)self;
    unsigned long long offset, count;
    if (!PyArg_ParseTuple(args, "KK", &offset, &count)) return NULL;
    if (datastore_ptr == MAP_FAILED) { PyErr_SetString(RuntimeError, "Trying to get data from frozen lib before initialization"); return NULL; }
    return PyMemoryView_FromMemory(datastore_ptr + offset, count, PyBUF_READ);
}


static PyObject*
index_for_name(PyObject *self, PyObject *args) {
    (void)self;
    const char *key;
    if (!PyArg_ParseTuple(args, "s", &key)) return NULL;
    long ans = get_perfect_hash_index_for_key(key);
    return PyLong_FromLong(ans);
}

static PyObject*
offsets_for_index(PyObject *self, PyObject *args) {
    (void)self;
    int index;
    if (!PyArg_ParseTuple(args, "i", &index)) return NULL;
    unsigned long offset, size;
    get_value_for_hash_index(index, &offset, &size);
    return Py_BuildValue("kk", offset, size);
}

static PyObject*
mode_for_path(PyObject *self, PyObject *args) {
    (void)self;
#ifdef _WIN32
    struct _stat statbuf;
    PyObject *pypath;
    if (!PyArg_ParseTuple(args, "U", &pypath)) return NULL;
    wchar_t *path = PyUnicode_AsWideCharString(pypath, NULL);
    if (!path) return NULL;
    int result = _wstat(path, &statbuf);
    PyMem_Free(path);
    if (result != 0) return PyErr_SetFromErrnoWithFilenameObject(OSError, pypath);
#else
    struct stat statbuf;
    const char *path;
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    if (stat(path, &statbuf) != 0) return PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
#endif
    return PyLong_FromLong(statbuf.st_mode);
}

static PyObject*
print(PyObject *self, PyObject *args) {
    (void)self;
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(args); i++) {
        PyObject *s = PyObject_Str(PyTuple_GET_ITEM(args, i));
        if (s != NULL) {
            fprintf(stderr, "%s", PyUnicode_AsUTF8(s));
            Py_DECREF(s);
            if (i != PyTuple_GET_SIZE(args) - 1) fprintf(stderr, " ");
        }
    }
    fprintf(stderr, "\n");
    RETURN_NONE;
}

static PyObject*
abspath(PyObject *self, PyObject *args) {
    (void)self;
#ifdef _WIN32
    PyObject *pypath;
    if (!PyArg_ParseTuple(args, "U", &pypath)) return NULL;
    wchar_t *path = PyUnicode_AsWideCharString(pypath, NULL);
    if (!path) return PyErr_NoMemory();
    DWORD sz = GetFullPathNameW(path, 0, NULL, NULL);
    wchar_t *resolved_path = PyMem_Calloc(sizeof(wchar_t), 2 * sz + 1);
    if (!resolved_path) { PyMem_Free(path); return PyErr_NoMemory(); }
    GetFullPathNameW(path, 2*sz, resolved_path, NULL);
    PyMem_Free(path);
    PyObject *ans = PyUnicode_FromWideChar(resolved_path, -1);
    PyMem_Free(resolved_path);
    return ans;
#else
    const char *path;
    char resolved_path[PATH_MAX+1] = {0};
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    if (realpath(path, resolved_path)) return PyUnicode_FromString(resolved_path);
    return PyTuple_GET_ITEM(args, 0);
#endif
}

static PyObject*
windows_expandvars(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *ans = NULL;
#ifdef _WIN32
    PyObject *pt;
    if (!PyArg_ParseTuple(args, "U", &pt)) return NULL;
    wchar_t *text = PyUnicode_AsWideCharString(pt, NULL);
    if (!text) return PyErr_NoMemory();
    LPWSTR dest = PyMem_Calloc(sizeof(wchar_t), 32 * 1024);
    if (!dest) { PyMem_Free(text); return PyErr_NoMemory(); }
    DWORD sz = ExpandEnvironmentStringsW(text, dest, 32 * 1024);
    PyMem_Free(text);
    if (sz > 32 * 1024 || sz < 1) { ans = pt;  Py_INCREF(pt); }
    ans = PyUnicode_FromWideChar(dest, sz - 1);
    PyMem_Free(dest);
#else
    (void)args;
    PyErr_SetString(PyExc_NotImplementedError, "Windows only");
#endif
    return ans;
}

static PyMethodDef bypy_methods[] = {
    {"windows_expandvars", (PyCFunction)windows_expandvars, METH_VARARGS,
     "windows_expandvars(key) -> Expand variables in the specified string"
    },
    {"get_home_directory", (PyCFunction)get_home_directory, METH_NOARGS,
     "get_home_directory() -> Return the home directory or empty string"
    },
    {"getenv", (PyCFunction)getenv_wrapper, METH_VARARGS,
     "getenv(key) -> Return value of specified env var or None"
    },
    {"read_file", (PyCFunction)read_file, METH_VARARGS,
     "read_file(path) -> read contents of file and return it"
    },
    {"setenv", (PyCFunction)setenv_wrapper, METH_VARARGS,
     "setenv(key, val=None) -> Set the specified env var"
    },
    {"mode_for_path", (PyCFunction)mode_for_path, METH_VARARGS,
     "mode_for_path(path) -> Return the mode for the specified path"
    },
    {"show_error_message", (PyCFunction)show_error_message, METH_VARARGS,
     "show_error_message(title, msg) -> Show an error message."
    },
    {"initialize_data_access", (PyCFunction)initialize_data_access, METH_VARARGS,
     "initialize_data_access(path) -> initialize access to the data store."
    },
    {"get_data_at", (PyCFunction)get_data_at, METH_VARARGS,
     "get_data_at(offset, count) -> return data of size count at offset as a memoryview."
    },
    {"index_for_name", (PyCFunction)index_for_name, METH_VARARGS,
     "index_for_name(key) -> index for name or -1 if name not present."
    },
    {"offsets_for_index", (PyCFunction)offsets_for_index, METH_VARARGS,
     "offsets_for_index(key) -> (offset, size)."
    },
    {"print", (PyCFunction)print, METH_VARARGS,
     "print(*args) -> print args to stderr useful as sys.stderr may not yet be ready"
    },
    {"abspath", (PyCFunction)abspath, METH_VARARGS,
     "abspath(path) -> return the absolute path for path"
    },
    {NULL}  /* Sentinel */
};


static struct PyModuleDef module = {
    /* m_base     */ PyModuleDef_HEAD_INIT,
    /* m_name     */ "bypy_frozen_importer",
    /* m_doc      */ "Utilities to implement importing in a frozen application",
    /* m_size     */ -1,
    /* m_methods  */ bypy_methods,
    /* m_slots    */ 0,
    /* m_traverse */ 0,
    /* m_clear    */ 0,
    /* m_free     */ 0,
};

static inline PyObject*
bypy_frozen_importer(void) {
    PyObject *m = PyModule_Create(&module);
#ifdef _WIN32
#define sep "\\"
#else
#define sep "/"
#endif
    if (m) {
        if (PyModule_AddStringConstant(m, "path_sep", sep) != 0) { Py_CLEAR(m); return NULL; }
    }
    return m;
}

static void
set_sys_string(const char* key, const wchar_t* val) {
    PyObject *temp = PyUnicode_FromWideChar(val, -1);
    if (temp) {
        if (PySys_SetObject(key, temp) != 0) fatal("Failed to set attribute on sys: %s", key);
        Py_DECREF(temp);
    } else {
        fatal("Failed to set attribute on sys, PyUnicode_FromWideChar failed");
    }
}

static void
set_sys_bool(const char* key, const bool val) {
	PyObject *pyval = PyBool_FromLong(val);
	if (PySys_SetObject(key, pyval) != 0) fatal("Failed to set attribute on sys: %s", key);
	Py_DECREF(pyval);
}


static void
bypy_pre_initialize_interpreter(bool use_os_log_) {
	if (PyImport_AppendInittab("bypy_frozen_importer", bypy_frozen_importer) == -1) {
		fatal("Failed to add bypy_frozen_importer to the init table");
	}
	use_os_log = use_os_log_;
    PyPreConfig preconfig;
    PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    preconfig.coerce_c_locale = 1;
    preconfig.isolated = 1;

    PyStatus status = Py_PreInitialize(&preconfig);
	if (PyStatus_Exception(status)) Py_ExitStatusException(status);
}

static void
show_error_during_setup() {
    // The interpreter is not fully setup so we cant rely on PyErr_Print()
    size_t sz = 0, pos = 0;
    char *errbuf = NULL;
#ifdef _WIN32
    const char *nl = "\r\n";
#else
    const char *nl = "\n";
#endif
#define A(...) { \
    if (sz - pos < 4096) { sz = sz ? 2 * sz : 8192; errbuf = realloc(errbuf, sz); if (!errbuf) return; } \
    pos += sn_printf(errbuf + pos, sz - pos - 1, __VA_ARGS__); \
}
#define P(fmt, ...) { A(fmt, __VA_ARGS__); pos += sn_printf(errbuf + pos, sz - pos - 1, "%s", nl); }

    P("%s", "There was an error initializing the bypy frozen importer:");
    PyObject *exc_type, *exc_val, *exc_tb;
    PyErr_Fetch(&exc_type, &exc_val, &exc_tb);
    PyErr_NormalizeException(&exc_type, &exc_val, &exc_tb);

    if (exc_type) {
        PyObject * temps = PyObject_Str(exc_type);
        if (temps) {
            const char *tempcstr = PyUnicode_AsUTF8(temps);
            if (tempcstr) A("%s: ", tempcstr);
            Py_DECREF(temps);
        }
    }

    if (exc_val) {
        PyObject * temps = PyObject_Str(exc_val);
        if (temps) {
            const char *tempcstr = PyUnicode_AsUTF8(temps);
            if (tempcstr) P("%s", tempcstr);
            Py_DECREF(temps);
        }
    }
    if (exc_tb) {
        P("%s", "Traceback (most recent call last):");
		PyTracebackObject *pactual_trace = (PyTracebackObject*)exc_tb;
        while (pactual_trace != NULL) {
			PyFrameObject *cur_frame = pactual_trace->tb_frame;
			const char *fname = PyUnicode_AsUTF8(cur_frame->f_code->co_filename);
            const char *func = PyUnicode_AsUTF8(cur_frame->f_code->co_name);
			int line = PyFrame_GetLineNumber(cur_frame);
            P("  File %s, line %d, in %s", fname ? fname : "<unknown file>", line, func ? func : "<unknown function>");
			pactual_trace = pactual_trace->tb_next;
		}
    }
    Py_CLEAR(exc_type); Py_CLEAR(exc_val); Py_CLEAR(exc_tb);
    fprintf(stderr, "%s", errbuf);
#ifdef _WIN32
    if (GUI_APP) {
        wchar_t *wbuf = calloc(pos+2, sizeof(wchar_t));
        if (wbuf) {
            MultiByteToWideChar(CP_UTF8, MB_PRECOMPOSED, errbuf, (int)pos, wbuf, (int)pos+2);
            show_windows_error_box(wbuf);
            free(wbuf);
        }
    }
#endif
    free(errbuf);
#undef A
#undef P
}

static inline PyObject*
module_dict_for_exec(const char *name) {
    // cloned from python source code
    _Py_IDENTIFIER(__builtins__);
    PyObject *m, *d = NULL;

    m = PyImport_AddModule(name);
    if (m == NULL) return NULL;
    d = PyModule_GetDict(m);
    if (d == NULL) { Py_DECREF(m); return NULL; }
    if (_PyDict_SetItemId(d, &PyId___builtins__, PyEval_GetBuiltins()) != 0) return NULL;
    return d;  // returning a borrowed reference
}

static inline int
bypy_setup_importer(const wchar_t *libdir) {
#ifdef _WIN32
    setup_windows_exceptions();
#endif
    int ok = 0;
    if (libdir == NULL) { fprintf(stderr, "Attempt to setup bypy importer with NULL libdir\n"); return ok; }
    PyObject *marshal = NULL, *loads = NULL, *importer_code = NULL;
    marshal = PyImport_ImportModule("marshal");
    if (marshal == NULL) goto error;
    loads = PyObject_GetAttrString(marshal, "loads");
    if (loads == NULL) goto error;
    importer_code = PyObject_CallFunction(loads, "y#", importer_script, arraysz(importer_script));
	if (importer_code == NULL) goto error;

    PyObject *d = module_dict_for_exec("bypy_importer");
    if (d == NULL) goto error;
    if (PyDict_SetItemString(d, "libdir", PyUnicode_FromWideChar(libdir, -1)) != 0) goto error;

	PyObject *pret = PyEval_EvalCode(importer_code, d, d);
	if (pret == NULL) goto error;
	Py_CLEAR(pret);
    ok = 1;
error:
    if (!ok) {
        show_error_during_setup();
        free_frozen_data();
    }
    Py_CLEAR(marshal); Py_CLEAR(loads); Py_CLEAR(importer_code);
    return ok;
}

static void
bypy_initialize_interpreter(
        const wchar_t *program_name, const wchar_t *home, const wchar_t *run_module, const wchar_t *libdir,
        int argc,
#ifdef _WIN32
        wchar_t* const *argv
#else
        char* const *argv
#endif
) {
#define CHECK_STATUS if (PyStatus_Exception(status)) { PyConfig_Clear(&config); Py_ExitStatusException(status); }
    PyStatus status;
    PyConfig config;

    PyConfig_InitIsolatedConfig(&config);
    config.module_search_paths_set = 1;
    config.optimization_level = 2;
    config.write_bytecode = 0;
    config.use_environment = 0;
    config.user_site_directory = 0;
    config.configure_c_stdio = 1;
    config.isolated = 1;
    config.install_signal_handlers = 1;
	config._init_main = 0;

    status = PyConfig_SetString(&config, &config.program_name, program_name);
    CHECK_STATUS;

#ifndef _WIN32
    status = PyConfig_SetString(&config, &config.home, home);
    CHECK_STATUS;
#endif
    status = PyConfig_SetString(&config, &config.run_module, run_module);
    CHECK_STATUS;

#ifdef _WIN32
    status = PyConfig_SetArgv(&config, argc, argv);
#else
    status = PyConfig_SetBytesArgv(&config, argc, argv);
#endif
    CHECK_STATUS;
    status = Py_InitializeFromConfig(&config);
    CHECK_STATUS;

    if (!bypy_setup_importer(libdir)) {
		PyConfig_Clear(&config);
        exit(1);
    }

	status = _Py_InitializeMain();
	CHECK_STATUS;
    PyConfig_Clear(&config);

#undef CHECK_STATUS
}

static int
bypy_run_interpreter(void) {
#ifdef _WIN32
    code_page = GetConsoleOutputCP();
    if (code_page != CP_UTF8) SetConsoleOutputCP(CP_UTF8);
    setup_vt_terminal_mode();
#endif

    int ret = Py_RunMain();

#ifdef _WIN32
    cleanup_console_state();
    Py_CLEAR(WindowsError); Py_CLEAR(OSError); Py_CLEAR(RuntimeError);
#endif
	free_frozen_data();
    return ret;
}
