include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs

println("Inicializando modelo...")
model = initialize_model()
println("Modelo creado con éxito")

# Ruta principal que Python consulta
route("/update") do
    try
        # Avanzar un paso en la simulación
        step!(model, 1)
        
        # Obtener posiciones de fantasmas y llaves
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys = [Tuple(a.pos) for a in allagents(model) if a isa Key && !a.collected]

        # Retornar JSON
        json(Dict(
            "ghosts" => ghosts,
            "keys" => keys
        ))
    catch e
        @error "Error en /update" exception=e
        json(Dict("error" => string(e)))
    end
end

# Ruta adicional para verificar el estado sin avanzar
route("/status") do
    try
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys = [Tuple(a.pos) for a in allagents(model) if a isa Key && !a.collected]

        json(Dict(
            "ghosts" => ghosts,
            "keys" => keys
        ))
    catch e
        @error "Error en /status" exception=e
        json(Dict("error" => string(e)))
    end
end

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

up(8000, host="0.0.0.0")