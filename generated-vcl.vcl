vcl 4.0;
import directors;

backend hello_kubernetes_minikube_http {
        .host = "10.0.2.15";
        .port = "30199";
}

backend test_minikube_foo {
        .host = "10.0.2.15";
        .port = "31158";
}

backend fallback_minikube_http {
        .host = "10.0.2.15";
        .port = "30655";
}

sub vcl_init {
    new dir_hello_kubernetes_http = directors.round_robin();
    dir_hello_kubernetes_http.add_backend(hello_kubernetes_minikube_http);

    new dir_test_foo = directors.round_robin();
    dir_test_foo.add_backend(test_minikube_foo);

    new dir_fallback_http = directors.round_robin();
    dir_fallback_http.add_backend(fallback_minikube_http);
}

sub vcl_recv {
    # hello-kubernetes
    if (req.http.host == "foo")
    {
      if (req.url ~ "^/hello") {
        set req.backend_hint = dir_hello_kubernetes_http.backend();
        return(pass);
      }
    }
    # fallback
    if (req.http.host == "foo")
    {
      if (req.url ~ "^/") {
        set req.backend_hint = dir_fallback_http.backend();
        return(pass);
      }
    }
}
