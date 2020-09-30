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
#endif
#include <stdlib.h>
#include <sys/stat.h>
#include <Python.h>
#include <stdio.h>
#include <string.h>
#include <bypy-data-index.h>
#include <bypy-importer.h>

static PyObject*
getenv_wrapper(PyObject *self, PyObject *args) {
    (void)self;
#ifdef _WIN32
    PyObject *pkey;
    if (!PyArg_ParseTuple(args, "U", &pkey)) return NULL;
    const wchar_t *wkey = PyUnicode_AsWideCharString(pkey);
    const wchar_t *wval = _wgetenv(wkey);
    PyMem_Free(wkey);
    if (!wval) Py_RETURN_NONE;
    return PyUnicode_FromWideChar(wval, -1);
#else
    const char *key;
    if (!PyArg_ParseTuple(args, "s", &key)) return NULL;
    const char *val = getenv(key);
    if (!val) Py_RETURN_NONE;
    return PyUnicode_FromString(val);
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
static HANDLE datastore_file_handle = INVALID_HANDLE_VALUE;
static HANDLE datastore_mmap_handle = INVALID_HANDLE_VALUE;
#else
static int datastore_fd = -1;
static void *datastore_ptr = MAP_FAILED;
static size_t datastore_len = 0;
#endif

static inline void
free_frozen_data(void) {
#ifdef _WIN32
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

static PyObject*
initialize_data_access(PyObject *self, PyObject *path) {
    (void)self;
    if (!PyUnicode_Check(path)) { PyErr_SetString(PyExc_TypeError, "path must be a string"); return NULL; }
    if (PyUnicode_READY(path) != 0) return NULL;
#ifdef _WIN32
    const wchar_t* wpath = PyUnicode_AsWideCharString(path);
    if (!wpath) return NULL;
    datastore_file_handle = CreateFileW(wpath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_READONLY | FILE_FLAG_RANDOM_ACCESS, NULL);
    PyMem_Free(wpath);
    if (datastore_file_handle == INVALID_HANDLE_VALUE) return PyErr_SetExcFromWindowsErrWithFilenameObject(PyExc_OSError, 0, path);
    datastore_mmap_handle = CreateFileMappingW(datastore_file_handle, NULL, PAGE_READONLY, 0, 0, NULL);
    if (datastore_mmap_handle == INVALID_HANDLE_VALUE) return PyErr_SetExcFromWindowsErrWithFilenameObject(PyExc_OSError, 0, path);
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
    if (datastore_ptr == MAP_FAILED) { PyErr_SetString(PyExc_RuntimeError, "Trying to get data from frozen lib before initialization"); return NULL; }
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
    const wchar_t *path = PyUnicode_AsWideCharString(pypath);
    if (!path) return PyErr_NoMemory();
    int result = _wstat(path, &statbuf);
    PyMem_Free(path);
    if (result != 0) return PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, pypath);
#else
    struct stat statbuf;
    const char *path;
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    if (stat(path, &statbuf) != 0) return PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
#endif
    return PyLong_FromLong(statbuf.st_mode);
}


static PyMethodDef methods[] = {
    {"getenv", (PyCFunction)getenv_wrapper, METH_VARARGS,
     "getenv(key) -> Return value of specified env var or None"
    },
    {"mode_for_path", (PyCFunction)mode_for_path, METH_VARARGS,
     "mode_for_path(path) -> Return the mode for the specified path"
    },
    {"show_error_message", (PyCFunction)show_error_message, METH_VARARGS,
     "show_error_message(title, msg) -> Show an error message."
    },
    {"initialize_data_access", (PyCFunction)initialize_data_access, METH_O,
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
    {NULL}  /* Sentinel */
};


static struct PyModuleDef module = {
    /* m_base     */ PyModuleDef_HEAD_INIT,
    /* m_name     */ "bypy_frozen_importer",
    /* m_doc      */ "Utilities to implement importing in a frozen application",
    /* m_size     */ -1,
    /* m_methods  */ methods,
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
print_error() {
    // TODO: Replace this with something that works even though interpreter is
    // not fully setup
    PyErr_Print();
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
bypy_setup_importer(PyObject *libdir) {
    if (libdir == NULL) { fprintf(stderr, "Attempt to setup bypy importer with NULL libdir\n"); return 0; }
    PyObject *importer_code = Py_CompileString(importer_script, "bypy-importer.py", Py_file_input);
	if (importer_code == NULL) goto error;

    PyObject *d = module_dict_for_exec("bypy_importer");
    if (d == NULL) goto error;
    if (PyDict_SetItemString(d, "libdir", libdir) != 0) goto error;

	PyObject *pret = PyEval_EvalCode(importer_code, d, d);
	Py_CLEAR(importer_code);
	if (pret == NULL) goto error;
	Py_CLEAR(pret);
    return 1;
error:
    print_error(); Py_CLEAR(importer_code); free_frozen_data(); return 0;
}
