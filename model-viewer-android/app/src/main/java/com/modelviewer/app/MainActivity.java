package com.modelviewer.app;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.View;
import android.webkit.MimeTypeMap;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private static final String HOST = "https://appassets.local/";
    private static final int REQ_FILES = 1;

    private WebView web;
    private ValueCallback<Uri[]> chooser;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setBackgroundColor(0xFF14161A);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                return serve(r.getUrl());
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try {
                    startActivityForResult(Intent.createChooser(i, "Fichiers 3D"), REQ_FILES);
                } catch (Exception e) {
                    chooser = null;
                    cb.onReceiveValue(null);
                    return false;
                }
                return true;
            }
        });
        load(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        load(intent);
    }

    private void load(Intent intent) {
        String url = HOST + "index.html";
        Uri data = intent == null ? null : intent.getData();
        if (data != null && Intent.ACTION_VIEW.equals(intent.getAction())) {
            String name = displayName(data);
            try {
                File f = new File(getCacheDir(), "open.bin");
                try (InputStream in = getContentResolver().openInputStream(data); OutputStream out = new FileOutputStream(f)) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                }
                url += "?open=1&name=" + Uri.encode(name);
            } catch (Exception ignored) { }
        }
        web.loadUrl(url);
    }

    private String displayName(Uri u) {
        try (Cursor c = getContentResolver().query(u, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (i >= 0) return c.getString(i);
            }
        } catch (Exception ignored) { }
        String p = u.getLastPathSegment();
        return p == null ? "model" : p.substring(p.lastIndexOf('/') + 1);
    }

    private WebResourceResponse serve(Uri u) {
        if (!"appassets.local".equals(u.getHost())) return null;
        String path = u.getPath() == null ? "/index.html" : u.getPath();
        if (path.equals("/")) path = "/index.html";
        try {
            InputStream in;
            if (path.startsWith("/open/")) in = new FileInputStream(new File(getCacheDir(), "open.bin"));
            else in = getAssets().open("www" + path);
            String ext = MimeTypeMap.getFileExtensionFromUrl(path);
            String mime = "application/octet-stream";
            if (path.endsWith(".js")) mime = "application/javascript";
            else if (path.endsWith(".wasm")) mime = "application/wasm";
            else if (path.endsWith(".html")) mime = "text/html";
            else if (ext != null && MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext) != null)
                mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
            return new WebResourceResponse(mime, "utf-8", in);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        }
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        if (req != REQ_FILES || chooser == null) return;
        Uri[] out = null;
        if (res == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int n = data.getClipData().getItemCount();
                out = new Uri[n];
                for (int i = 0; i < n; i++) out[i] = data.getClipData().getItemAt(i).getUri();
            } else if (data.getData() != null) out = new Uri[]{data.getData()};
        }
        chooser.onReceiveValue(out);
        chooser = null;
    }

    @Override
    public void onBackPressed() {
        finish();
    }

    @Override
    protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
