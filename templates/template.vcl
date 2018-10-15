vcl 4.0;

import directors;

{% for service in services %}
  {% if service.spec.type != "NodePort" %}
    {% continue %}
  {% endif %}
  {% for port in service.spec.ports %}
    {% for node in nodes %}
backend {{service.metadata.name|c_ident}}_{{ node.metadata.name|c_ident }}_{{ port.name|c_ident}} {
      {% for address in node.status.addresses %}
        {% if address.type == "InternalIP"%}
        .host = "{{address.address}}";
        .port = "{{port.nodePort}}";
        {% endif %}
      {% endfor %}
}
    {% endfor %}
  {% endfor %}
{% endfor %}

sub vcl_init {
{% for service in services %}
  {% if service.spec.type != "NodePort" %}
    {% continue %}
  {% endif %}
  {% for port in service.spec.ports %}
    new dir_{{service.metadata.name|c_ident}}_{{ port.name|c_ident}} = directors.round_robin();
    {% for node in nodes %}
    dir_{{service.metadata.name|c_ident}}_{{ port.name|c_ident}}.add_backend({{service.metadata.name|c_ident}}_{{ node.metadata.name|c_ident }}_{{ port.name|c_ident}});
    {% endfor %}
  {% endfor %}
{% endfor %}
}

sub vcl_recv {
{% for ingress in ingresses|sort_by_priority %}
    # {{ ingress.metadata.name }}
  {% for rule in ingress.spec.rules %}
    {% if rule.host %}
    if (req.http.host == "{{rule.host}}")
    {% endif %}
    {
    {% for path in rule.http.paths %}
      if (req.url ~ "^{{ path.path }}") {
        set req.backend_hint = dir_{{path.backend.serviceName|c_ident}}_{{ path.backend.servicePort|c_ident}}.backend();
        {% if ingress.metadata.annotations.remove_prefix %}
        set req.url = regsub(req.url, "^{{ ingress.metadata.annotations.remove_prefix }}", "/");
        {% endif %}
        return(pass);
      }
    }
    {% endfor %}
  {% endfor %}
{% endfor %}
}